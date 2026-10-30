<script setup lang="ts">
import {ref, watch} from 'vue'
import axios from 'axios'
import {ElMessage} from 'element-plus'
import type {ModelSettings} from '../types/recruitment'
import {errorMessage} from '../utils/errors'
import {modelConfig, modelConfigComplete} from '../utils/model'

const visible=defineModel<boolean>('visible',{required:true})
const settings=defineModel<ModelSettings>('settings',{required:true})
defineProps<{serverMode:string|undefined}>()
const testing=ref(false)
const status=ref<'success'|'error'|null>(null)
const message=ref('')
let generation=0
watch(()=>[settings.value.mode,settings.value.model,settings.value.base_url,settings.value.api_key],()=>{
 generation++;status.value=null;message.value=''
})
function finish(){
 if(!modelConfigComplete(settings.value)){ElMessage.warning('请填写模型名称和兼容接口地址');return}
 visible.value=false
}
async function testConnection(){
 if(testing.value)return
 if(!modelConfigComplete(settings.value)){ElMessage.warning('请填写模型名称和兼容接口地址');return}
 const requested=generation
 testing.value=true;status.value=null;message.value=''
 try{
  const {data}=await axios.post('/api/v1/model/test',modelConfig(settings.value))
  if(requested===generation){status.value='success';message.value=`连接成功：${data.model}，耗时 ${data.elapsed_ms} 毫秒`}
 }catch(e){if(requested===generation){status.value='error';message.value=errorMessage(e)}}
 finally{testing.value=false}
}
</script>

<template>
 <el-dialog v-model="visible" title="模型设置" width="min(480px, 94vw)">
  <div class="model-settings-form">
   <p>选择当前页面的处理模式。自定义配置只在页面内存中使用，刷新后需重新填写；API Key 不写入浏览器存储或数据库。</p>
   <el-radio-group v-model="settings.mode">
    <el-radio value="demo">规则演示（无需模型）</el-radio>
    <el-radio value="server">服务器配置</el-radio>
    <el-radio value="custom">自定义模型</el-radio>
   </el-radio-group>
   <div v-if="settings.mode==='server'" class="settings-note">{{serverMode==='model'?'服务器已配置模型。':'服务器当前使用规则演示。'}}</div>
   <template v-if="settings.mode==='custom'">
    <label>模型名称<el-input v-model="settings.model" placeholder="输入服务提供的模型名称"/></label>
    <label>OpenAI 兼容接口地址<el-input v-model="settings.base_url" placeholder="https://服务地址/v1"/></label>
    <label>API Key<el-input v-model="settings.api_key" type="password" show-password autocomplete="off" placeholder="无鉴权时可留空"/></label>
    <div class="settings-note">密钥仅随当前请求发送。远程地址携带密钥时须使用 HTTPS。</div>
   </template>
   <div v-if="settings.mode!=='demo'" class="model-connectivity">
    <button class="plain-button" :disabled="testing" @click="testConnection">{{testing?'正在测试…':'测试模型连接'}}</button>
    <p v-if="status" role="status" :class="status==='success'?'connection-success':'connection-error'">{{message}}</p>
   </div>
  </div>
  <template #footer><button class="primary-button" @click="finish">完成</button></template>
 </el-dialog>
</template>
