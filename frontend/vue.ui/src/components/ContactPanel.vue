<script setup>
import {reactive,watch,ref,onBeforeUnmount} from 'vue'
import {useRouter} from 'vue-router'
import {api,session} from '../services/api.js'
import {createContact} from '../services/contact.js'
const props=defineProps({propertyId:String}),router=useRouter();
const contact=createContact(api);
const ui=reactive({busy:false,data:null,message:'',status:0,retryAt:0});
let sequence=0;const clock=ref(Date.now());const timer=setInterval(()=>clock.value=Date.now(),1000);
const reset=()=>{sequence++;contact.reset();Object.assign(ui,contact.state)};
watch(()=>[props.propertyId,session.user?.id,session.token],reset);
onBeforeUnmount(()=>{clearInterval(timer);reset()});
async function reveal(){if(!session.token)return router.push({path:'/login',query:{reason:'login-required'}});const run=++sequence;ui.busy=true;await contact.reveal(props.propertyId);if(run===sequence)Object.assign(ui,contact.state)}
const telephone=value=>/^\+?[0-9 ().-]{5,30}$/.test(value||'')?'tel:'+value.replace(/[ ().-]/g,''):null;
const email=value=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value||'')?'mailto:'+value:null;
</script>
<template><div class="mt-5 space-y-3" data-testid="contact-panel" aria-live="polite">
<button v-if="!ui.data?.available" type="button" class="w-full py-3 rounded-full bg-[#1E325A] text-white text-xs disabled:opacity-50" :disabled="ui.busy||clock<ui.retryAt" @click="reveal">{{ui.busy?'Đang tải liên hệ…':'Xem liên hệ'}}</button>
<p v-if="ui.message" :role="ui.status?'alert':'status'" class="text-xs">{{ui.message}}</p>
<template v-if="ui.data?.available"><p v-if="ui.data.contactName" class="text-sm font-semibold">{{ui.data.contactName}}</p>
<p v-if="ui.data.contactPhone" class="break-all text-sm"><a v-if="telephone(ui.data.contactPhone)" :href="telephone(ui.data.contactPhone)" class="underline">{{ui.data.contactPhone}}</a><span v-else>{{ui.data.contactPhone}}</span></p>
<p v-if="ui.data.contactEmail" class="break-all text-sm"><a v-if="email(ui.data.contactEmail)" :href="email(ui.data.contactEmail)" class="underline">{{ui.data.contactEmail}}</a><span v-else>{{ui.data.contactEmail}}</span></p></template>
<p v-if="clock<ui.retryAt" class="text-xs">Có thể thử lại sau {{Math.ceil((ui.retryAt-clock)/1000)}} giây.</p>
</div></template>
