export function safeLoginDestination(value,role){
 if(typeof value==='string'&&value.startsWith('/')&&!value.startsWith('//')&&!/[\\\s\u0000-\u001f]/.test(value)){
  const path=value.split(/[?#]/)[0]
  if(/^\/(home|listings|map|valuation|advisor|market|favorites|my-listing|projects|listing|account|post)(\/[^?#]*)?$/.test(path))return value
 }
 return role==='ADMIN'?'/admin':'/home'
}
