<script setup>
import {computed} from 'vue'
import PrivateImage from './PrivateImage.vue'
import {price,displayDecimal,types,states} from '../../services/property.js'
const props=defineProps({property:{type:Object,required:true},own:Boolean,list:Boolean})
const detail=computed(()=>({path:'/listing/'+props.property.id,query:props.own?{own:'1'}:{}}))
const cover=computed(()=>(props.property.images?.find(i=>i.cover)||props.property.images?.[0])?.url)
</script>
<template>
 <article class="property-card" :class="{'property-card-list':list}">
  <RouterLink :to="detail" class="property-main" :aria-label="'Xem chi tiết '+property.title">
   <div class="property-image"><PrivateImage :src="cover" :alt="property.title"/><span class="property-badge">{{own?states[property.status]:property.transactionType==='SALE'?'Bán':'Cho thuê'}}</span></div>
   <div class="property-body"><p class="property-type">{{types[property.propertyType]}}</p><h3>{{property.title}}</h3><p class="property-location">{{[property.district,property.city].filter(Boolean).join(', ')||property.address||'Chưa có địa chỉ'}}</p><p class="property-price">{{price(property)}}</p><div class="property-specs"><span>{{displayDecimal(property.areaSqmExact??property.areaSqm)}} m²</span><template v-if="property.propertyType!=='LAND'"><span v-if="property.bedrooms>0">{{property.bedrooms}} phòng ngủ</span><span v-if="property.bathrooms>0">{{property.bathrooms}} phòng tắm</span></template></div></div>
  </RouterLink>
  <div class="property-actions"><RouterLink :to="detail" class="detail-link">Xem chi tiết ↗</RouterLink><slot/></div>
 </article>
</template>
<style scoped>
.property-card{min-width:0;overflow:hidden;display:flex;flex-direction:column;background:white;border:1px solid #e7e1d7;border-radius:24px;color:#142b4f;transition:transform .2s,box-shadow .2s}.property-card:hover{transform:translateY(-3px);box-shadow:0 15px 35px #142b4f12}.property-main{display:block;color:inherit;text-decoration:none;flex:1;min-width:0}.property-image{height:245px;position:relative;overflow:hidden;background:#e5e4dd}.property-image :deep(img){width:100%;height:100%;object-fit:cover;transition:transform .3s}.property-card:hover .property-image :deep(img){transform:scale(1.025)}.property-badge{position:absolute;top:16px;left:16px;background:#fffffff0;padding:7px 13px;border-radius:30px;font-size:11px;font-weight:600}.property-body{padding:22px 22px 0;min-width:0}.property-type{font-size:10px;letter-spacing:.08em;color:#947244}.property-body h3{font-size:19px;line-height:1.5;font-weight:600;margin:10px 0;overflow-wrap:anywhere}.property-location{font-size:12px;line-height:1.6;color:#748092;overflow-wrap:anywhere}.property-price{font-size:21px;font-weight:650;line-height:1.5;margin:17px 0;overflow-wrap:anywhere}.property-specs{display:flex;flex-wrap:wrap;gap:10px 16px;border-top:1px solid #edeae4;padding-top:15px;font-size:12px;color:#637083}.property-actions{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;padding:20px 22px}.detail-link{border-radius:30px;background:#142b4f;color:white;text-decoration:none;font-size:12px;font-weight:600;padding:11px 18px}.property-card :focus-visible{outline:3px solid #b3915f;outline-offset:-3px}@media(min-width:768px){.property-card-list .property-main{display:grid;grid-template-columns:38% 1fr}.property-card-list .property-image{height:100%;min-height:260px}.property-card-list .property-actions{justify-content:flex-end}}@media(max-width:600px){.property-image{height:220px}.property-price{font-size:20px}}
</style>
