<script setup>
import {ref,watch} from 'vue'
import {api} from '../services/api.js'
import {types} from '../services/property.js'
const props=defineProps({district:String}),summary=ref(null),busy=ref(false),error=ref(''),type=ref('');let sequence=0;
async function load(){const run=++sequence;busy.value=true;error.value='';summary.value=null;try{const q=new URLSearchParams({transactionType:'SALE',priceUnit:'TOTAL'});if(props.district)q.set('district',props.district);if(type.value)q.set('propertyType',type.value);const result=await api('/properties/market-summary?'+q,{authenticated:false});if(run===sequence)summary.value=result}catch{if(run===sequence)error.value='Chưa tải được giá chào hiện tại. Vui lòng thử lại.'}finally{if(run===sequence)busy.value=false}}
watch(()=>[props.district,type.value],load,{immediate:true});
const price=value=>value==null?'—':Number(value).toLocaleString('vi-VN',{maximumFractionDigits:0});
</script>
<template><section id="market" class="bg-[#F1EEE8] py-20"><div class="mx-auto max-w-7xl px-5 lg:px-8"><p class="text-xs tracking-widest text-[#B3915F]">MARKET INTELLIGENCE</p><h2 class="mt-3 text-4xl font-semibold">Giá chào <span class="text-[#B3915F]">hiện tại.</span></h2>
<p class="mt-4 text-sm">Tin bán được duyệt còn hiệu lực · VND / tổng giá. Đây là giá chào, chưa có dữ liệu lịch sử hoặc giá giao dịch.</p>
<label class="mt-5 block text-sm">Loại bất động sản <select v-model="type" class="ml-3 rounded border bg-white p-3"><option value="">Tất cả</option><option v-for="(label,key) in types" :key="key" :value="key">{{label}}</option></select></label>
<p v-if="busy" role="status">Đang tải thống kê…</p><p v-if="error" role="alert">{{error}} <button @click="load" class="underline">Thử lại</button></p>
<div v-if="summary" class="mt-8 grid gap-4 md:grid-cols-3"><div class="rounded-2xl bg-white p-6"><p>Tin phù hợp</p><strong class="text-3xl">{{summary.overall.count}}</strong></div><div class="rounded-2xl bg-white p-6"><p>Giá chào trung bình</p><strong>{{price(summary.overall.averageAskingPrice)}} VND</strong></div><div class="rounded-2xl bg-white p-6"><p>Giá chào theo tổng diện tích</p><strong>{{price(summary.overall.weightedAskingPricePerSqm)}} VND/m²</strong></div></div>
<p v-if="summary?.overall.count===0" class="mt-4">Chưa có tin đủ điều kiện để thống kê.</p><ul v-if="summary?.byDistrict?.length" class="mt-6 grid gap-3 md:grid-cols-3"><li v-for="g in summary.byDistrict" :key="g.key" class="rounded-xl bg-white p-4">{{g.key||'Chưa xác định khu vực'}} · {{g.amounts.count}} tin · {{price(g.amounts.weightedAskingPricePerSqm)}} VND/m²</li></ul><p v-if="summary?.districtsTruncated">Danh sách thống kê khu vực đã được giới hạn bởi server.</p>
</div></section></template>
