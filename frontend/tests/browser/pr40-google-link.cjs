const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
const {chromium}=require(process.env.PR40_BROWSER_PLAYWRIGHT || 'playwright-core');
(async()=>{
 const frontend=path.resolve(__dirname, '../..');
 process.env.VITE_ENABLE_REFRESH='true';
 const {createServer}=await import(pathToFileURL(path.join(frontend,'node_modules/vite/dist/node/index.js')).href);
 const vite=await createServer({root:frontend,server:{host:'127.0.0.1',port:0}});
 await vite.listen();
 const origin='http://127.0.0.1:'+vite.httpServer.address().port;
 let browser;
 try {
  browser=await chromium.launch({executablePath:process.env.PR40_BROWSER_EXECUTABLE,headless:true});
  let passed=0;
  for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
   for(const scenario of ['success','cancel','expired','conflict']){
    let startCount=0,completions=0,linked=false,loggedOut=false,auths=0;
    const ctx=await browser.newContext({viewport,serviceWorkers:'block'});
    try {
     const page=await ctx.newPage();
     const me={id:41,email:'owner@example.test',fullName:'Fixture Owner',role:'BUYER',status:'ACTIVE',emailVerified:true};
     await ctx.route('**/api/**',async route=>{
      const req=route.request(),p=new URL(req.url()).pathname;
      const json=(data,status=200)=>route.fulfill({status,json:data});
      if(p.endsWith('/auth/csrf'))return json({headerName:'X-CSRF-TOKEN',token:'fixture-csrf'});
      if(p.endsWith('/auth/refresh'))return json({accessToken:'fixture-only',user:me});
      if(p.endsWith('/auth/logout')){loggedOut=true;return json({});}
      if(p.endsWith('/users/me'))return json(me);
      if(p.endsWith('/users/me/valuation-history'))return json({items:[],totalPages:0});
      if(p.endsWith('/auth/google/link/status'))return json({available:true,linked});
      if(p.endsWith('/auth/google/link/start')){
       startCount++;
       assert.equal(req.headers().authorization,'Bearer fixture-only');
       assert.equal(req.headers()['x-csrf-token'],'fixture-csrf');
       if(req.postDataJSON().currentPassword==='incorrect')return json({code:'WRONG_PASSWORD',message:'Mật khẩu hiện tại không chính xác'},400);
       return json({authorizationPath:'/auth/oauth2/link/authorize/google'});
      }
      if(p.endsWith('/auth/oauth2/link/authorize/google')){
       auths++;
       return route.fulfill({status:302,headers:{Location:origin+'/auth/google/link/complete'+(scenario==='cancel'?'?status=failed':'')}});
      }
      if(p.endsWith('/auth/google/link/complete')){
       completions++;assert.equal(req.headers().authorization,'Bearer fixture-only');
       if(scenario==='expired')return json({code:'GOOGLE_LINK_EXPIRED',message:'Yêu cầu liên kết đã hết hạn'},410);
       if(scenario==='conflict')return json({code:'GOOGLE_IDENTITY_CONFLICT',message:'Tài khoản Google đã được liên kết'},409);
       linked=true;return json({linked:true});
      }
      return json({});
     });
     await page.goto(origin+'/account',{waitUntil:'domcontentloaded'});
     const form=page.locator('form').filter({has:page.getByRole('button',{name:'Liên kết Google',exact:true})});
     await form.locator('input[type=password]').fill('incorrect');
     await form.getByRole('button',{name:'Liên kết Google'}).click();
     await page.getByText('Mật khẩu hiện tại không chính xác',{exact:true}).waitFor();
     assert.equal(await form.locator('input[type=password]').inputValue(),'');
     assert.equal(auths,0);assert.equal(loggedOut,false);
     assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
     await form.locator('input[type=password]').fill('correct-fixture');
     await form.getByRole('button',{name:'Liên kết Google'}).click();
     await page.waitForURL('**/auth/google/link/complete*');
     if(scenario==='success'){
      await page.getByText(/Google đã được liên kết với tài khoản SmartProp của bạn/).waitFor();
     }else{
      const text={cancel:/Không thể xác minh tài khoản Google/,expired:/Yêu cầu liên kết đã hết hạn/,conflict:/Tài khoản Google đã được liên kết/}[scenario];
      await page.getByRole('alert').filter({hasText:text}).waitFor();
     }
     assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
     await page.getByRole('button',{name:/Quay lại Hồ sơ/}).click();
     await page.waitForURL('**/account');
     await page.getByText(scenario==='success'?'Đã liên kết Google với tài khoản SmartProp này.':'Chưa liên kết Google với tài khoản SmartProp này.', {exact:true}).waitFor();
     assert.equal(auths,1);assert.equal(startCount,2);assert.equal(completions,scenario==='cancel'?0:1);
     assert.equal(loggedOut,false);passed++;console.log(viewport.width+' '+scenario+' PASS');
    }finally{await ctx.close();}
   }
  }
  console.log(passed+' browser scenarios PASS with HTTP fixtures');
 }finally{await browser?.close();await vite.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
