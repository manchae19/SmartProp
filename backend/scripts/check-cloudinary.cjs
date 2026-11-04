const fs=require('fs'),os=require('os'),path=require('path'),cp=require('child_process'),net=require('net'),crypto=require('crypto');
const root=path.resolve(__dirname,'../..'),work=fs.mkdtempSync(path.join(os.tmpdir(),'smartprop-cloudinary-test-')),home=process.env.SMARTPROP_TEST_MYSQL_HOME||'C:/Program Files/MySQL/MySQL Server 8.0',bin=home+'/bin',schema='smartprop_cloudinary_test_'+crypto.randomBytes(6).toString('hex'),data=path.join(work,'data');
let server,port;const delay=ms=>new Promise(r=>setTimeout(r,ms));
function run(exe,args,input){const r=cp.spawnSync(exe,args,{input,encoding:'utf8',windowsHide:true});if(r.status)throw Error((r.stderr||r.error?.message||'Process failed').slice(-2000));return r.stdout}
(async()=>{const probe=net.createServer();await new Promise(r=>probe.listen(0,'127.0.0.1',r));port=probe.address().port;await new Promise(r=>probe.close(r));if(port===3306)throw Error('Unsafe test target');
run(bin+'/mysqld.exe',['--no-defaults','--initialize-insecure','--basedir='+home,'--datadir='+data,'--log-error='+path.join(work,'init.log')]);
try{
 server=cp.spawn(bin+'/mysqld.exe',['--no-defaults','--basedir='+home,'--datadir='+data,'--bind-address=127.0.0.1','--port='+port,'--mysqlx=0','--skip-log-bin','--log-error='+path.join(work,'server.log')],{windowsHide:true,stdio:'ignore'});
 const args=['--no-defaults','--protocol=TCP','--host=127.0.0.1','--port='+port,'--user=root'];
 let ready=false;for(let i=0;i<100;i++){try{run(bin+'/mysql.exe',args,'SELECT 1');ready=true;break}catch{}if(server.exitCode!==null)throw Error('Test server exited');await delay(250)}if(!ready)throw Error('Test server timeout');
 run(bin+'/mysql.exe',args,'CREATE DATABASE '+schema+' CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;');
 const maven=process.env.MAVEN_HOME||path.join(os.homedir(),'.m2/wrapper/dists/apache-maven-3.9.11/03d7e36a140982eea48e22c1dcac01d8862b2550b2939e09a0809bbc5182a5bc');
 const log=fs.openSync(path.join(work,'test.log'),'w');
 const command=['-Dmaven.home='+maven,'-Dclassworlds.conf='+maven+'/bin/m2.conf','-Dmaven.multiModuleProjectDirectory='+root+'/backend','-classpath',maven+'/boot/plexus-classworlds-2.9.0.jar','org.codehaus.plexus.classworlds.launcher.Launcher','-o','-B','-ntp','-DforkCount=0','-Dsmartprop.build.directory='+path.join(work,'build'),'-Dtest=CloudinarySyncIntegrationTest,CloudinaryAdminClientTest,CloudinaryImageDeliveryTest,CloudinaryMediaAccessTest','test'];
 const result=cp.spawnSync(process.env.JAVA_HOME?path.join(process.env.JAVA_HOME,'bin/java.exe'):'C:/Program Files/Eclipse Adoptium/jdk-21.0.12.101-hotspot/bin/java.exe',command,{cwd:root+'/backend',env:{...process.env,SMARTPROP_CLOUDINARY_TEST_URL:'jdbc:mysql://127.0.0.1:'+port+'/'+schema+'?connectionTimeZone=UTC&allowPublicKeyRetrieval=true&useSSL=false'},windowsHide:true,stdio:['ignore',log,log]});fs.closeSync(log);
 console.log(fs.readFileSync(path.join(work,'test.log'),'utf8').split('\n').slice(-48).join('\n'));if(result.status)throw Error('Cloudinary verification failed: '+work);
 fs.writeFileSync(path.join(work,'result.json'),JSON.stringify({passed:true,port,schema,work},null,2));console.log('PASSED. Isolated artifacts: '+work);
}finally{if(server&&server.exitCode===null){cp.spawnSync(bin+'/mysqladmin.exe',['--no-defaults','--protocol=TCP','--host=127.0.0.1','--port='+port,'--user=root','shutdown'],{windowsHide:true,stdio:'ignore',timeout:15000});for(let i=0;i<50&&server.exitCode===null;i++)await delay(100);if(server.exitCode===null)server.kill()}}
})().catch(e=>{console.error(e.message);process.exitCode=1});
