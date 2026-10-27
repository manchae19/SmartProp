import {reactive} from 'vue'
import {createHttpClient} from './httpClient.js'
export const session=reactive({token:null,user:null})
export const refreshEnabled=import.meta.env?.VITE_ENABLE_REFRESH==='true'
const baseUrl=(import.meta.env?.VITE_API_BASE_URL||'/api/v1').replace(/\/$/,'')
let client
export function clearSession(){client?.invalidate();session.token=null;session.user=null;globalThis.localStorage?.removeItem('token');globalThis.localStorage?.removeItem('role')}
clearSession()
client=createHttpClient({baseUrl,session,refreshEnabled,clear:clearSession,expired:()=>window.dispatchEvent(new Event('smartprop:session-expired')),lock:globalThis.navigator?.locks?run=>navigator.locks.request('smartprop-refresh',run):null})
// Cross-tab logout sends no credentials, token or profile. Web Locks serializes cookie rotation.
const channel=typeof window!=='undefined'&&window.location&&typeof BroadcastChannel!=='undefined'?new BroadcastChannel('smartprop-session'):null
if(channel)channel.onmessage=e=>{if(e.data==='logout'){clearSession();window.dispatchEvent(new Event('smartprop:session-expired'))}}
export const api=(path,options)=>client.request(path,options)
export const restoreSession=()=>client.restore()
export function errorText(error){if(error.status===503&&['FEATURE_DISABLED','FEATURE_UNAVAILABLE'].includes(error.code))return 'Tính năng chưa được bật trên máy chủ. Vui lòng liên hệ quản trị viên.';return [error.message,...Object.entries(error.fields||{}).map(([key,value])=>key+': '+value)].join(' — ')}
export async function login(email,password){const value=email.trim(),result=await client.login({email:value.toLowerCase()==='admin'?'admin@smartprop.local':value,password});client.invalidate();session.token=result.accessToken;session.user=result.user;return result.user}
export const register=body=>api('/auth/register',{method:'POST',body:{...body,email:body.email.trim()},authenticated:false})
export async function loadProfile(){session.user=await api('/users/me');return session.user}
export async function logout(){await client.logout();channel?.postMessage('logout')}
