const fs=require('node:fs');
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const root=process.env.SMARTPROP_BACKEND || path.resolve(__dirname,'../../backend');
const mysql=process.env.MYSQL_EXECUTABLE || 'mysql';
const args=process.env.MYSQL_OPTIONS_FILE ? [`--defaults-extra-file=${process.env.MYSQL_OPTIONS_FILE}`] : ['--no-defaults'];
args.push('--protocol=TCP',`--host=${process.env.DB_TEST_HOST||'127.0.0.1'}`,`--port=${process.env.DB_TEST_PORT||'3306'}`,`--user=${process.env.DB_TEST_USER||'root'}`,'--default-character-set=utf8mb4','--batch','--skip-column-names');
const db='smartprop_dbcheck_'+Date.now();
let count=0;
const report=[];
function execute(sql,database=db){return spawnSync(mysql,[...args,...(database?[database]:[])],{input:sql,encoding:'utf8',maxBuffer:8*1024*1024});}
function q(sql,database=db){const r=execute(sql,database);if(r.status!==0)throw Error(r.stderr.trim());return r.stdout.trim();}
function pass(name){count++;report.push('PASS '+name);console.log('PASS '+name);}
function equal(name,sql,expected){const actual=q(sql);if(actual!==String(expected))throw Error(name+': expected '+expected+', got '+actual);pass(name);}
function rejected(name,sql,errorCode){const r=execute('START TRANSACTION;\n'+sql+'\nROLLBACK;');if(r.status===0 || !r.stderr.includes('ERROR '+errorCode+' '))throw Error(name+': expected MySQL '+errorCode+', got '+r.stderr.trim());pass(name);}
function migrate(database,skipV1=false){const files=fs.readdirSync(path.resolve(root,'../database/migrations')).filter(f=>/^V\d+__.*\.sql$/.test(f)).sort((a,b)=>+a.match(/^V(\d+)/)[1]-+b.match(/^V(\d+)/)[1]);for(const f of files){if(skipV1&&f.startsWith('V1__'))continue;q(fs.readFileSync(path.resolve(root,'../database/migrations',f),'utf8'),database);}return files;}
const version=q('SELECT VERSION();',null);
q(`CREATE DATABASE ${db} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;`,null);
const files=migrate(db);pass('clean migration '+files.join(', '));
equal('34 domain tables',"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE();",34);
q(`INSERT INTO users(email,password_hash,full_name,role,status,created_at,updated_at) VALUES
 ('buyer@smartprop.example.test','TEST_FIXTURE_ONLY_NOT_A_LOGIN_HASH','Synthetic Buyer','BUYER','ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)),
 ('broker@smartprop.example.test','TEST_FIXTURE_ONLY_NOT_A_LOGIN_HASH','Synthetic Broker','BROKER','ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));`);
const seed=fs.readFileSync(path.resolve(root,'../database/seeds/development.sql'),'utf8');
const fixture=path.join(root,'dev-fixtures/sample-property.svg');
for(let i=0;i<2;i++)q(`START TRANSACTION; SET @fixture_bytes=${fs.statSync(fixture).size};\n${seed}\nCOMMIT;`);
equal('seed repeat-safe',"SELECT CONCAT((SELECT COUNT(*) FROM properties),',',(SELECT COUNT(*) FROM property_images),',',(SELECT COUNT(*) FROM saved_properties),',',(SELECT COUNT(*) FROM reports));",'1,1,1,1');
equal('existing role bridge',"SELECT COUNT(*) FROM user_roles;",2);
q("UPDATE users SET role='BUYER' WHERE email='broker@smartprop.example.test';");
equal('role update bridge',"SELECT role_code FROM user_roles WHERE user_id=(SELECT id FROM users WHERE email='broker@smartprop.example.test');",'BUYER');
q("UPDATE users SET role='BROKER' WHERE email='broker@smartprop.example.test';");
rejected('case-insensitive email unique',"INSERT INTO users(email,password_hash,full_name,role,status,created_at,updated_at) VALUES('BUYER@smartprop.example.test','fixture','Duplicate','BUYER','ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));",1062);
rejected('duplicate favorite',"INSERT INTO saved_properties(user_id,property_id) SELECT id,'20000000-0000-4000-8000-000000000001' FROM users WHERE email='buyer@smartprop.example.test';",1062);
rejected('favorite missing FK',"INSERT INTO saved_properties(user_id,property_id) VALUES(-1,'20000000-0000-4000-8000-000000000001');",1452);
rejected('negative property price',"UPDATE properties SET price=-1;",3819);
rejected('zero area',"UPDATE properties SET area_sqm=0;",3819);
rejected('sale/month mismatch',"UPDATE properties SET price_unit='PER_MONTH';",3819);
rejected('negative bedrooms',"UPDATE properties SET bedrooms=-1;",3819);
rejected('unknown property state',"UPDATE properties SET status='APPROVE_BY_AI';",3819);
rejected('zero content version',"UPDATE properties SET content_version=0;",3819);
rejected('invalid JSON',"UPDATE properties SET declared_amenities='{broken';",3140);
rejected('amenities object instead of array',"UPDATE properties SET declared_amenities=JSON_OBJECT();",3819);
const imageInsert=`INSERT INTO property_images(id,property_id,uploaded_by,storage_key,mime_type,byte_size,sort_order,is_cover) SELECT '30000000-0000-4000-8000-000000000002','20000000-0000-4000-8000-000000000001',id,'fixture/2','image/png',100,1,TRUE FROM users WHERE email='broker@smartprop.example.test';`;
rejected('only one active cover',imageInsert,1062);
rejected('only one active sort order',imageInsert.replace('100,1,TRUE','100,0,FALSE'),1062);
q(`START TRANSACTION; UPDATE property_images SET deleted_at=UTC_TIMESTAMP(6); ${imageInsert.replace('100,1,TRUE','100,0,TRUE')} ROLLBACK;`);pass('soft-deleted image frees cover/order');
rejected('nonpositive image size',"UPDATE property_images SET byte_size=0;",3819);
rejected('delete user with business records restricted',"DELETE FROM users WHERE email='broker@smartprop.example.test';",1451);
rejected('delete property with evidence restricted',"DELETE FROM properties;",1451);
rejected('resolved report requires evidence',"UPDATE reports SET status='RESOLVED';",3819);
rejected('duplicate user role',"INSERT INTO user_roles(user_id,role_code) SELECT id,'BUYER' FROM users WHERE email='buyer@smartprop.example.test';",1062);
const buyer=Number(q("SELECT id FROM users WHERE email='buyer@smartprop.example.test';"));
q(`INSERT INTO auth_sessions(id,user_id,created_at,expires_at) VALUES('00000000-0000-4000-8000-000000000001',${buyer},UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)+INTERVAL 1 HOUR); UPDATE auth_sessions SET revoked=TRUE;`);
equal('legacy revocation writes timestamp',"SELECT revoked_at IS NOT NULL FROM auth_sessions;",1);
q(`INSERT INTO password_reset_tokens(id,user_id,token_hash,expires_at) VALUES('00000000-0000-4000-8000-000000000002',${buyer},REPEAT('a',64),UTC_TIMESTAMP(6)+INTERVAL 1 HOUR);`);
rejected('reset token hash unique',`INSERT INTO password_reset_tokens(id,user_id,token_hash,expires_at) VALUES('00000000-0000-4000-8000-000000000003',${buyer},REPEAT('a',64),UTC_TIMESTAMP(6)+INTERVAL 1 HOUR);`,1062);
const distance=Number(q("SELECT ST_Distance_Sphere((SELECT location FROM properties LIMIT 1),(SELECT location FROM points_of_interest LIMIT 1));"));
if(distance<100||distance>110)throw Error('GIS distance incorrect: '+distance);pass('GIS distance in meters (longitude difference 0.001 at Da Nang)');
equal('GIS longitude latitude order',"SELECT CONCAT(ROUND(ST_Longitude(location),2),',',ROUND(ST_Latitude(location),2)) FROM properties LIMIT 1;",'108.22,16.06');
rejected('incorrect SRID',"UPDATE properties SET location=ST_GeomFromText('POINT(108.22 16.06)',0);",3643);
equal('spatial indexes',"SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema=DATABASE() AND index_type='SPATIAL';",2);
const explain=q("EXPLAIN SELECT id FROM properties WHERE status='PENDING' ORDER BY created_at LIMIT 20;");
if(!explain.includes('ix_properties_moderation'))throw Error('Missing moderation index plan');pass('moderation query uses supporting index');
q(`INSERT INTO model_versions(id,kind,name,version,status,artifact_key,artifact_sha256) VALUES
 ('60000000-0000-4000-8000-000000000001','VALUATION','fixture','1','DRAFT','TEST_ONLY',REPEAT('a',64)),
 ('60000000-0000-4000-8000-000000000002','SIMILARITY','fixture','1','DRAFT','TEST_ONLY',REPEAT('b',64)),
 ('60000000-0000-4000-8000-000000000003','AMENITY','fixture','1','DRAFT','TEST_ONLY',REPEAT('c',64));
 INSERT INTO ai_config_versions(id,kind,version,approved_by) VALUES
 ('70000000-0000-4000-8000-000000000001','VALUATION','1',${buyer}),
 ('70000000-0000-4000-8000-000000000002','SIMILARITY','1',${buyer}),
 ('70000000-0000-4000-8000-000000000003','AMENITY','1',${buyer});`);
rejected('deployment model kind mismatch',`INSERT INTO ai_deployments(kind,model_version_id,config_version_id,updated_by) VALUES('VALUATION','60000000-0000-4000-8000-000000000002','70000000-0000-4000-8000-000000000001',${buyer});`,1452);
for(let i=1;i<=3;i++){const kind=['VALUATION','SIMILARITY','AMENITY'][i-1];q(`INSERT INTO ai_tasks(id,property_id,task_type,execution_mode,model_version_id,config_version_id,input_content_version,input_snapshot,idempotency_key) VALUES('80000000-0000-4000-8000-00000000000${i}','20000000-0000-4000-8000-000000000001','${kind}','ASYNC','60000000-0000-4000-8000-00000000000${i}','70000000-0000-4000-8000-00000000000${i}',1,JSON_OBJECT('fixture',true),'fixture-${i}'); INSERT INTO ai_task_attempts(id,task_id,attempt_no,lease_token,worker_id,lease_expires_at) VALUES('90000000-0000-4000-8000-00000000000${i}','80000000-0000-4000-8000-00000000000${i}',1,'a0000000-0000-4000-8000-00000000000${i}','fixture',UTC_TIMESTAMP(6)+INTERVAL 1 MINUTE);`);}
rejected('task idempotency unique',"UPDATE ai_tasks SET idempotency_key='fixture-1' WHERE task_type='SIMILARITY';",1062);
rejected('retry capped at one retry',"UPDATE ai_tasks SET max_attempts=3;",3819);
rejected('attempt beyond limit',"UPDATE ai_task_attempts SET attempt_no=3;",3819);
const valuation="INSERT INTO valuation_results(id,task_id,attempt_id,reference_price,price_unit,base_value,model_output,output_scale,latency_ms) VALUES('b0000000-0000-4000-8000-000000000001','80000000-0000-4000-8000-000000000001','90000000-0000-4000-8000-000000000001',1,'TOTAL',0,1,'PRICE',1);";
q(valuation);pass('valuation linked to matching attempt');
rejected('valuation cannot use other task attempt',valuation.replace('b0000000-0000-4000-8000-000000000001','b0000000-0000-4000-8000-000000000002').replace('90000000-0000-4000-8000-000000000001','90000000-0000-4000-8000-000000000002'),1452);
q("INSERT INTO image_index_versions(id,embedding_model_id,version,artifact_key,vector_dimension,metric) VALUES('c0000000-0000-4000-8000-000000000001','60000000-0000-4000-8000-000000000002','1','TEST_ONLY',128,'COSINE'); INSERT INTO image_embeddings(index_version_id,image_id,faiss_vector_id) VALUES('c0000000-0000-4000-8000-000000000001','30000000-0000-4000-8000-000000000001',1); INSERT INTO image_similarity_runs(id,task_id,attempt_id,index_version_id,source_image_id,property_id,threshold,top_k,latency_ms) VALUES('d0000000-0000-4000-8000-000000000001','80000000-0000-4000-8000-000000000002','90000000-0000-4000-8000-000000000002','c0000000-0000-4000-8000-000000000001','30000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000001',0.9,5,1);");
rejected('similarity result must have index embedding',"INSERT INTO image_matches(run_id,index_version_id,matched_image_id,`rank`,similarity_score) VALUES('d0000000-0000-4000-8000-000000000001','c0000000-0000-4000-8000-000000000001','30000000-0000-4000-8000-000000000099',1,0.95);",1452);
q("INSERT INTO amenity_analysis_results(id,task_id,attempt_id,property_id,latency_ms,comparison) VALUES('e0000000-0000-4000-8000-000000000001','80000000-0000-4000-8000-000000000003','90000000-0000-4000-8000-000000000003','20000000-0000-4000-8000-000000000001',1,JSON_ARRAY());");
equal('successful zero-detection result retained',"SELECT COUNT(*) FROM amenity_analysis_results;",1);
rejected('detection confidence range',"INSERT INTO amenity_detections(id,analysis_id,property_id,image_id,class_name,confidence) VALUES('f0000000-0000-4000-8000-000000000001','e0000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000001','30000000-0000-4000-8000-000000000001','sofa',1.5);",3819);
// An independent populated-V1 upgrade verifies that legacy account data is preserved.
const upgrade=db+'_upgrade';q(`CREATE DATABASE ${upgrade} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;`,null);
q(fs.readFileSync(path.resolve(root,'../database/migrations/V1__accounts_and_sessions.sql'),'utf8'),upgrade);
q("INSERT INTO users(email,password_hash,full_name,role,status,created_at,updated_at) VALUES('legacy@example.test','TEST_ONLY','Legacy','BROKER','ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));",upgrade);
migrate(upgrade,true);
if(q("SELECT CONCAT(id,':',role,':',password_hash) FROM users WHERE email='legacy@example.test';",upgrade)!=='1:BROKER:TEST_ONLY')throw Error('V1 upgrade changed legacy user');pass('populated V1 upgrade preserves id/role/password');
if(q("SELECT role_code FROM user_roles WHERE user_id=1;",upgrade)!=='BROKER')throw Error('V1 role backfill failed');pass('populated V1 role membership backfill');
const summary={checkedAt:new Date().toISOString(),serverVersion:version,schemas:[db,upgrade],checksPassed:count,flywayExecuted:false,javaCompiled:false,dockerExecuted:false,report};
const output=process.env.DB_CHECK_REPORT || path.resolve(process.cwd(),'database-check-results.json');
fs.writeFileSync(output,JSON.stringify(summary,null,2));
console.log(`${count} checks passed on MySQL ${version}. Test-only schemas retained: ${db}, ${upgrade}. No production database was accessed.`);
