const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),net=require('node:net'),crypto=require('node:crypto'),cp=require('node:child_process'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),work=fs.mkdtempSync(path.join(os.tmpdir(),'smartprop-listing-codes-'));
const home=process.env.SMARTPROP_TEST_MYSQL_HOME||'C:/Program Files/MySQL/MySQL Server 8.0',bin=path.join(home,'bin');
const schema='smartprop_listing_test_'+crypto.randomBytes(6).toString('hex');
const data=path.join(work,'data'),quiet={windowsHide:true,stdio:'ignore'},uuid=()=>crypto.randomUUID();
const delay=ms=>new Promise(r=>setTimeout(r,ms));
let server,port;
function execute(exe,args,sql){const r=cp.spawnSync(exe,args,{input:sql,encoding:'utf8',windowsHide:true,maxBuffer:8*1024*1024});if(r.status!==0)throw Error((r.stderr||r.error?.message||'Command failed').slice(-3000));return r.stdout.replace(/\r\n/g,'\n').trim();}
const args=()=>['--no-defaults','--protocol=TCP','--host=127.0.0.1','--port='+port,'--user=root','--default-character-set=utf8mb4','--batch','--skip-column-names',schema];
const sql=s=>execute(path.join(bin,'mysql.exe'),args(),s);
function row(id,title='Isolated fixture',deleted=false,extra=''){
 return "INSERT INTO properties(id,owner_id,title,property_type,transaction_type,price,price_unit,area_sqm,location,status,content_version,deleted_at"+extra+") VALUES ('"+id+"',1,'"+title+"','APARTMENT','SALE',2000000000,'TOTAL',60,ST_GeomFromText('POINT(108.23 16.06)',4326,'axis-order=long-lat'),'DRAFT',1,"+(deleted?"UTC_TIMESTAMP(6)":"NULL")+(extra?",'SP001'":"")+");";
}
async function start(){
 server=cp.spawn(path.join(bin,'mysqld.exe'),['--no-defaults','--basedir='+home,'--datadir='+data,'--bind-address=127.0.0.1','--port='+port,'--mysqlx=0','--skip-log-bin','--log-error='+path.join(work,'server.log')],quiet);
 for(let i=0;i<80;i++){if(server.exitCode!==null)throw Error('Isolated MySQL exited; see '+work);try{execute(path.join(bin,'mysql.exe'),args().slice(0,-1),'SELECT 1');return}catch{}await delay(250)}
 throw Error('Isolated MySQL readiness timed out');
}
async function stop(){if(!server||server.exitCode!==null)return;const child=server;cp.spawnSync(path.join(bin,'mysqladmin.exe'),['--no-defaults','--protocol=TCP','--host=127.0.0.1','--port='+port,'--user=root','shutdown'],{...quiet,timeout:15000});for(let i=0;i<50&&child.exitCode===null;i++)await delay(100);if(child.exitCode===null)child.kill();}
function parallelSql(statement){return new Promise((resolve,reject)=>{let out='',err='';const child=cp.spawn(path.join(bin,'mysql.exe'),args(),{windowsHide:true});child.stdout.on('data',c=>out+=c);child.stderr.on('data',c=>err+=c);child.on('error',reject);child.on('close',code=>code?reject(Error(err)):resolve(out.trim()));child.stdin.end(statement)})}
(async()=>{
 const probe=net.createServer();await new Promise(r=>probe.listen(0,'127.0.0.1',r));port=probe.address().port;await new Promise(r=>probe.close(r));
 if(port===3306||!/^smartprop_listing_test_[a-f0-9]+$/.test(schema))throw Error('Unsafe test target');
 execute(path.join(bin,'mysqld.exe'),['--no-defaults','--initialize-insecure','--basedir='+home,'--datadir='+data,'--log-error='+path.join(work,'initialize.log')]);
 try{
 await start();
 execute(path.join(bin,'mysql.exe'),args().slice(0,-1),'CREATE DATABASE '+schema+' CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;');
 const migrations=fs.readdirSync(path.join(root,'database/migrations')).filter(n=>/^V[0-9]+__.*[.]sql$/.test(n)).sort((a,b)=>parseInt(a.slice(1))-parseInt(b.slice(1)));
 for(const name of migrations.filter(n=>parseInt(n.slice(1))<=15))sql(fs.readFileSync(path.join(root,'database/migrations',name),'utf8').replace(/^\uFEFF/,''));
 sql("INSERT INTO users(id,email,password_hash,full_name,role,status,created_at,updated_at) VALUES(1,'isolated@example.invalid','not-a-login-credential','Isolated fixture','BROKER','ACTIVE',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));");
 const ids=['00000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000003'];
 for(const [i,id] of ids.entries())sql(row(id,'Backfill '+i,i===1));
 const snapshot="SELECT id,owner_id,IFNULL(project_id,''),title,status,IFNULL(deleted_at,''),ST_AsText(location),created_at,updated_at FROM properties WHERE id IN ('"+ids.join("','")+"') ORDER BY id;";
 const before=sql(snapshot);
 const mavenHome=process.env.MAVEN_HOME||path.join(os.homedir(),'.m2/wrapper/dists/apache-maven-3.9.11/03d7e36a140982eea48e22c1dcac01d8862b2550b2939e09a0809bbc5182a5bc');
 const java=process.env.JAVA_HOME?path.join(process.env.JAVA_HOME,'bin/java.exe'):'C:/Program Files/Eclipse Adoptium/jdk-21.0.12.101-hotspot/bin/java.exe';
 const javaArgs=['-Dmaven.home='+mavenHome,'-Dclassworlds.conf='+mavenHome+'/bin/m2.conf','-Dmaven.multiModuleProjectDirectory='+path.join(root,'backend'),'-classpath',path.join(mavenHome,'boot/plexus-classworlds-2.9.0.jar'),'org.codehaus.plexus.classworlds.launcher.Launcher','-o','-B','-ntp','-DforkCount=0','-Dsmartprop.build.directory='+path.join(work,'build'),'-Dtest=ListingCodeIntegrationTest','test'];
 const log=fs.openSync(path.join(work,'jpa-test.log'),'w');
 const env={...process.env,SMARTPROP_LISTING_TEST_URL:'jdbc:mysql://127.0.0.1:'+port+'/'+schema+'?connectionTimeZone=UTC&allowPublicKeyRetrieval=true&useSSL=false'};
 const result=cp.spawnSync(java,javaArgs,{cwd:path.join(root,'backend'),env,windowsHide:true,stdio:['ignore',log,log]});fs.closeSync(log);
 if(result.status!==0)throw Error('JPA/Flyway test failed: '+fs.readFileSync(path.join(work,'jpa-test.log'),'utf8').split('\n').slice(-65).join('\n'));
 assert.equal(sql(snapshot),before,'Backfill changed original listing fields');
 assert.equal(sql("SELECT listing_code FROM properties WHERE id IN ('"+ids.join("','")+"') ORDER BY created_at,id;"),'SP001\nSP002\nSP003');
 assert.equal(sql("SELECT IS_NULLABLE FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='properties' AND column_name='listing_code'"),'NO');
 assert.equal(sql("SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='properties' AND column_name='listing_code' AND non_unique=0"),'1');
 const newIds=Array.from({length:32},uuid);
 const codes=await Promise.all(newIds.map(id=>parallelSql(row(id)+"SELECT listing_code FROM properties WHERE id='"+id+"';")));
 assert.equal(new Set(codes).size,32);assert(codes.every(c=>/^SP[0-9]{3,}$/.test(c)));
 const target=newIds[0],old=sql("SELECT listing_code FROM properties WHERE id='"+target+"';");
 let immutable=false;try{sql("UPDATE properties SET listing_code='SP999999' WHERE id='"+target+"';")}catch(e){immutable=e.message.includes('listing_code is immutable')}assert(immutable);
 sql("UPDATE properties SET title='Changed',deleted_at=UTC_TIMESTAMP(6) WHERE id='"+target+"';");assert.equal(sql("SELECT listing_code FROM properties WHERE id='"+target+"';"),old);
 const largest=sql("SELECT id,listing_code FROM properties ORDER BY CAST(SUBSTRING(listing_code,3) AS UNSIGNED) DESC LIMIT 1").split('\t');
 sql("DELETE FROM properties WHERE id='"+largest[0]+"';");
 assert.equal(sql("SELECT COUNT(*) FROM property_listing_code_allocations WHERE property_id='"+largest[0]+"'"),'1');
 const afterDelete=uuid();sql(row(afterDelete));assert(BigInt(sql("SELECT SUBSTRING(listing_code,3) FROM properties WHERE id='"+afterDelete+"'"))>BigInt(largest[1].slice(2)));
 sql('ALTER TABLE property_listing_code_allocations AUTO_INCREMENT=999;');
 const edge=uuid(),overflow=uuid();sql(row(edge)+row(overflow));assert.equal(sql("SELECT listing_code FROM properties WHERE id='"+edge+"'"),'SP999');assert.equal(sql("SELECT listing_code FROM properties WHERE id='"+overflow+"'"),'SP1000');
 const chosen=uuid();sql(row(chosen,'No chosen code',false,',listing_code'));assert.notEqual(sql("SELECT listing_code FROM properties WHERE id='"+chosen+"'"),'SP001');
 await stop();await start();const restarted=uuid();sql(row(restarted));assert(BigInt(sql("SELECT SUBSTRING(listing_code,3) FROM properties WHERE id='"+restarted+"'"))>1000n);
 const report={passed:true,mysql:sql('SELECT VERSION()'),schema,port,concurrentInserts:32,backfilled:3,uuidAndOriginalFieldsUnchanged:true,nonNullAndUnique:true,immutable:true,deletedCodeNotReused:true,beyond999:true,restartVerified:true,jpaAndFlywayVerified:true,work};
 fs.writeFileSync(path.join(work,'result.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
 }finally{await stop()}
})().catch(e=>{console.error(e.message);console.error('Artifacts: '+work);process.exitCode=1});
