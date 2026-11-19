const {chromium}=await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';
const browser=await chromium.launch({channel:process.env.PLAYWRIGHT_CHANNEL || (process.platform==='win32'?'msedge':undefined),headless:true});
try {
  const page=await browser.newPage({viewport:{width:1280,height:900}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  const seen=[];
  const options={model_version:'v6',model_run:'b4b1339d3f35857e',categories:[{category:'Nhà ở',locations:['Hải Châu']},{category:'Đất nền',locations:['Hải Châu']},{category:'Căn hộ chung cư',locations:['Hải Châu']}],
    location_labels:{'Hải Châu':'Hải Châu'},access_types:{alley:'Kiệt/hẻm',frontage:'Mặt tiền'},house_subtypes:{villa:'Biệt thự',house_c4:'Nhà cấp 4'},
    v1_3:{available:true,real_features_enabled:true,supported_categories:['Nhà ở','Đất nền','Căn hộ chung cư']}};
  await page.route('**/api/v1/**',route=>route.fulfill({status:401,json:{message:'fixture unauthenticated'}}));
  await page.route('**/api/ai/**',async route=>{
    const path=new URL(route.request().url()).pathname;
    if(path.endsWith('/model/options'))return route.fulfill({json:options});
    const payload=route.request().postDataJSON();seen.push({path,payload});
    const v13=path.endsWith('v1_3_preview');
    return route.fulfill({json:{model_version:v13?'v1.3':'v6',category:payload.category,currency:'VND',is_preview:v13,status:'PREVIEW_EXPERIMENTAL',price_band:'2-3B',
      predicted_asking_price_vnd:2500000000,features_used:{area_sqm:payload.area_sqm,location_feature:payload.location_feature},missing_features:[],warnings:[],
      shap_explanation:{top_factors:[{feature_name:'area_sqm',shap_value:0.1,impact_pct:5,label:'Diện tích'}]}}});
  });
  await page.goto((process.env.SMARTPROP_TEST_ORIGIN || 'http://127.0.0.1:15173')+'/valuation');
  await page.getByRole('combobox',{name:'Mô hình tham khảo'}).waitFor();
  await page.getByRole('textbox',{name:'Điền nhanh địa bàn từ địa chỉ'}).fill('Phường Hải Châu 1, quận Hải Châu, Đà Nẵng');
  await page.getByRole('button',{name:'Điền địa bàn',exact:true}).click();
  await page.getByRole('spinbutton',{name:'Diện tích (m²)',exact:true}).fill('80');
  await page.getByRole('spinbutton',{name:'Chiều rộng đường/hẻm (m)',exact:true}).fill('7.5');
  await page.getByRole('button',{name:'Ước tính giá rao',exact:true}).click();
  await page.getByRole('heading',{name:'Yếu tố tác động đến giá (SHAP)'}).waitFor();
  assert.equal(seen[0].payload.road_width_m,7.5);
  assert.equal(seen[0].payload.location_feature,'Hải Châu');
  await page.getByRole('combobox',{name:'Mô hình tham khảo'}).selectOption('v6');
  await page.getByRole('button',{name:'Ước tính giá rao',exact:true}).click();
  await page.getByTestId('estimated-price').waitFor();
  assert.equal(seen[1].path,'/api/ai/predict');
  assert.equal('road_width_m' in seen[1].payload,false);
  await page.getByRole('link',{name:'Đăng nhập để lưu kết quả'}).waitFor();
  assert.deepEqual(errors,[]);
  console.log('PASS: React valuation UI, quick address, V1.3 optional measurements, SHAP, V6 switching and history boundary. Mock API fixtures; not model accuracy.');
} finally {await browser.close();}
