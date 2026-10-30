<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import DateTimePicker from './DateTimePicker.vue'
import type {AppRow} from './types/recruitment'
import {errorMessage as errorText} from './utils/errors'

type Candidate = {id:string;name:string;education:string|null;skills:string|null;work_years:number|null}
type Position = {id:string;title:string}
type Interview = {id:string;application_id:string;application_stage:string;candidate_name:string;position:string;round_no:number;interviewer:string|null;scheduled_at:string|null;status:string;result:string;evaluation:string|null}
const props=defineProps<{rows:AppRow[];transcriptBusy:boolean}>()
const emit=defineEmits<{refresh:[];view:[id:string];uploadTranscript:[file:File,interviewId:string,applicationId:string]}>()
const tab=ref('applications')
const candidates=ref<Candidate[]>([])
const positions=ref<Position[]>([])
const interviews=ref<Interview[]>([])
const busy=ref(false)
let loadGeneration=0
const search=ref('')
const filteredRows=computed(()=>props.rows.filter(r=>`${r.candidate_name}${r.position}${r.id}`.toLowerCase().includes(search.value.toLowerCase())))
const dialog=ref(false)
const mode=ref<'create'|'edit'>('create')
const applicationId=ref('')
const form=ref({candidate_id:'',candidate_name:'',position_id:'',name:'',phone:'',email:'',education:'',skills:'',work_years:null as number|null,owner:'hr-demo',version:1})
const resumeDialog=ref(false)
const resumeApp=ref<AppRow|null>(null)
const resumeText=ref('')
const screeningDialog=ref(false)
const screeningApp=ref<AppRow|null>(null)
const screeningForm=ref({evaluation:'',decision:'PENDING'})
const interviewDialog=ref(false)
const interviewMode=ref<'action'|'edit'>('action')
const interviewId=ref('')
const interviewCompleted=ref(false)
const interviewForm=ref({application_id:'',action:'schedule' as 'schedule'|'feedback',round_no:1,scheduled_at:'',interviewer:'',evaluation:'',decision:'PENDING'})
const canUpload=(row:Interview)=>row.status==='SCHEDULED'&&row.application_stage===`ROUND${row.round_no}_SCHEDULED`
function chooseTranscript(event:Event,row:Interview){
 const input=event.target as HTMLInputElement
 const file=input.files?.[0]
 if(file)emit('uploadTranscript',file,row.id,row.application_id)
 input.value=''
}

async function load(){
 const generation=++loadGeneration
 try{
  const [c,p,i]=await Promise.all([axios.get('/api/v1/candidates'),axios.get('/api/v1/positions'),axios.get('/api/v1/management/interviews')])
  if(generation!==loadGeneration)return
  candidates.value=c.data;positions.value=p.data;interviews.value=i.data
 }catch(e){if(generation===loadGeneration)ElMessage.error(errorText(e))}
}
function create(){
 mode.value='create';applicationId.value=''
 form.value={candidate_id:'',candidate_name:'',position_id:'',name:'',phone:'',email:'',education:'',skills:'',work_years:null,owner:'hr-demo',version:1}
 dialog.value=true
}
async function edit(row:AppRow){
 try{
  const {data}=await axios.get(`/api/v1/applications/${row.id}`)
  mode.value='edit';applicationId.value=row.id
  form.value={candidate_id:data.candidate.id,candidate_name:'',position_id:'',name:data.candidate.name,phone:data.candidate.phone||'',email:data.candidate.email||'',
   education:data.candidate.education||'',skills:data.candidate.skills||'',work_years:data.candidate.work_years,
   owner:data.application.owner,version:data.application.version}
  dialog.value=true
 }catch(e){ElMessage.error(errorText(e))}
}
async function save(){
 if(busy.value)return
 const f=form.value
 if(mode.value==='create'&&(!f.position_id||(!f.candidate_id&&!f.candidate_name.trim()))){ElMessage.warning('请选择岗位，并选择或填写候选人');return}
 if(mode.value==='edit'&&(!f.name.trim()||!f.owner.trim())){ElMessage.warning('请填写候选人姓名和负责人');return}
 busy.value=true
 try{
  if(mode.value==='create')await axios.post('/api/v1/management/applications',{candidate_id:f.candidate_id||null,candidate_name:f.candidate_name||null,position_id:positions.value.some(p=>p.id===f.position_id)?f.position_id:null,position_title:positions.value.some(p=>p.id===f.position_id)?null:f.position_id,phone:f.phone||null,email:f.email||null,education:f.education||null,skills:f.skills||null,work_years:f.work_years,owner:f.owner})
  else await axios.put(`/api/v1/management/applications/${applicationId.value}`,{name:f.name,phone:f.phone||null,email:f.email||null,education:f.education||null,skills:f.skills||null,work_years:f.work_years,owner:f.owner,version:f.version})
  dialog.value=false;ElMessage.success('已保存');emit('refresh');await load()
 }catch(e){ElMessage.error(errorText(e))}finally{busy.value=false}
}
function openResume(row:AppRow){resumeApp.value=row;resumeText.value='';resumeDialog.value=true}
async function uploadResume(event:Event){
 const input=event.target as HTMLInputElement;const file=input.files?.[0]
 if(!file||!resumeApp.value||busy.value)return
 const data=new FormData();data.append('file',file);busy.value=true
 try{await axios.post(`/api/v1/management/applications/${resumeApp.value.id}/resumes`,data);ElMessage.success('简历已关联候选人');resumeDialog.value=false;emit('refresh')}
 catch(e){ElMessage.error(errorText(e))}finally{busy.value=false;input.value=''}
}
async function saveManualResume(){
 if(!resumeApp.value||busy.value)return
 if(!resumeText.value.trim()){ElMessage.warning('请填写简历内容');return}
 busy.value=true
 try{await axios.post(`/api/v1/management/applications/${resumeApp.value.id}/resumes/manual`,{text:resumeText.value});ElMessage.success('人工简历已保存');resumeDialog.value=false;emit('refresh')}
 catch(e){ElMessage.error(errorText(e))}finally{busy.value=false}
}
function openScreening(row:AppRow){screeningApp.value=row;screeningForm.value={evaluation:'',decision:'PENDING'};screeningDialog.value=true}
async function saveScreening(){
 if(!screeningApp.value||busy.value)return
 if(!screeningForm.value.evaluation.trim()){ElMessage.warning('请填写初筛评价');return}
 busy.value=true
 try{await axios.post(`/api/v1/management/applications/${screeningApp.value.id}/screening`,screeningForm.value);screeningDialog.value=false;ElMessage.success('初筛结果已保存');emit('refresh');await load()}
 catch(e){ElMessage.error(errorText(e))}finally{busy.value=false}
}
function progress(row:AppRow){
 if(row.stage==='SCREENING'){openScreening(row);return}
 const match=row.stage.match(/^ROUND([123])_(PENDING|SCHEDULED|FEEDBACK)$/)
 if(!match){ElMessage.warning('当前阶段无法安排面试或记录反馈');return}
 newInterview();interviewForm.value.application_id=row.id;interviewForm.value.round_no=Number(match[1]);interviewForm.value.action=match[2]==='PENDING'?'schedule':'feedback'
}
async function confirmEmployment(row:AppRow){
 if(busy.value)return
 const target=row.stage==='OFFER_PENDING'?'OFFER_ACCEPTED':'HIRED'
 const label=target==='OFFER_ACCEPTED'?'候选人已接受 Offer':'候选人已入职'
 try{
  await ElMessageBox.confirm(`确认${row.candidate_name}${label.replace('候选人','')}？`,label,{type:'warning',confirmButtonText:'确认',cancelButtonText:'取消'})
  busy.value=true
  await axios.post(`/api/v1/management/applications/${row.id}/employment-action`,{target})
  ElMessage.success('招聘进度已更新');emit('refresh');await load()
 }catch(e){if(e!=='cancel'&&e!=='close')ElMessage.error(errorText(e))}finally{busy.value=false}
}
function newInterview(){
 interviewMode.value='action';interviewId.value='';interviewCompleted.value=false
 interviewForm.value={application_id:'',action:'schedule',round_no:1,scheduled_at:'',interviewer:'',evaluation:'',decision:'PENDING'}
 interviewDialog.value=true
}
function editInterview(row:Interview){
 interviewMode.value='edit';interviewId.value=row.id;interviewCompleted.value=row.status==='COMPLETED'
 interviewForm.value={application_id:row.application_id,action:'schedule',round_no:row.round_no,scheduled_at:row.scheduled_at||'',interviewer:row.interviewer||'',evaluation:row.evaluation||'',decision:row.result}
 interviewDialog.value=true
}
async function saveInterview(){
 if(busy.value)return
 const f=interviewForm.value
 if(!f.application_id){ElMessage.warning('请选择关联申请');return}
 busy.value=true
 try{
  if(interviewMode.value==='action')await axios.post(`/api/v1/management/applications/${f.application_id}/interview-actions`,f)
  else await axios.put(`/api/v1/management/interviews/${interviewId.value}`,{scheduled_at:f.scheduled_at,interviewer:f.interviewer||null,evaluation:f.evaluation||null})
  interviewDialog.value=false;ElMessage.success('面试记录已保存');emit('refresh');await load()
 }catch(e){ElMessage.error(errorText(e))}finally{busy.value=false}
}
onMounted(load)
onBeforeUnmount(()=>{loadGeneration++})
watch(()=>props.rows,load)
</script>

<template>
 <div class="page-intro"><span class="eyebrow">CANDIDATE MANAGEMENT</span><h1>候选人管理</h1><p>建档与简历 → 人工初筛 → 安排面试 → 记录评价与结论 → 下一轮。各步骤均由人工确认。</p></div>
 <div class="panel management-panel">
  <el-tabs v-model="tab">
   <el-tab-pane label="候选人与申请" name="applications">
    <div class="management-toolbar"><div class="search-field"><input v-model="search" placeholder="搜索姓名、岗位或申请 ID"/></div><span>{{filteredRows.length}} 条申请</span><button class="primary-button" @click="create">新建候选人 / 申请</button></div>
    <el-table :data="filteredRows" class="clean-table" stripe empty-text="暂无申请记录">
     <el-table-column prop="candidate_name" label="候选人" min-width="120"/><el-table-column prop="position" label="应聘岗位" min-width="150"/><el-table-column prop="stage_label" label="招聘阶段" min-width="130"/><el-table-column prop="owner" label="负责人" min-width="110"/>
     <el-table-column label="操作" min-width="260"><template #default="s"><div class="management-actions"><button class="link-action" @click="edit(s.row)">编辑</button><button class="link-action" @click="openResume(s.row)">简历</button><button v-if="s.row.stage==='SCREENING'||/^ROUND[123]_(PENDING|SCHEDULED|FEEDBACK)$/.test(s.row.stage)" class="link-action" @click="progress(s.row)">{{s.row.stage==='SCREENING'?'初筛':s.row.stage.endsWith('_PENDING')?'安排面试':'记录反馈'}}</button><button v-if="['OFFER_PENDING','OFFER_ACCEPTED'].includes(s.row.stage)" class="link-action" :disabled="busy" @click="confirmEmployment(s.row)">{{s.row.stage==='OFFER_PENDING'?'确认接受 Offer':'确认入职'}}</button><button class="link-action" @click="emit('view',s.row.id)">详情</button></div></template></el-table-column>
    </el-table>
   </el-tab-pane>
   <el-tab-pane label="面试记录" name="interviews">
    <div class="management-toolbar"><span>{{interviews.length}} 条面试 · 待进行的面试可上传全文</span><button class="primary-button" @click="newInterview">安排面试 / 记录反馈</button></div>
    <el-table :data="interviews" class="clean-table" stripe empty-text="暂无面试记录">
     <el-table-column prop="candidate_name" label="候选人" min-width="100"/><el-table-column prop="position" label="岗位" min-width="145"/><el-table-column label="轮次" width="75"><template #default="s">{{s.row.round_no}} 面</template></el-table-column><el-table-column prop="scheduled_at" label="面试时间" min-width="145"/><el-table-column prop="interviewer" label="面试官" min-width="100"/><el-table-column label="状态" width="90"><template #default="s">{{s.row.status==='SCHEDULED'?'待进行':'已完成'}}</template></el-table-column><el-table-column label="结论" width="85"><template #default="s">{{s.row.result==='PASS'?'通过':s.row.result==='REJECT'?'未通过':'待定'}}</template></el-table-column><el-table-column label="操作" min-width="155"><template #default="s"><div class="management-actions"><button class="link-action" @click="editInterview(s.row)">编辑</button><label v-if="canUpload(s.row)" class="link-action table-transcript-picker">{{props.transcriptBusy?'处理中…':'上传文字'}}<input type="file" accept=".txt,.pdf,.docx" :disabled="props.transcriptBusy" @change="chooseTranscript($event,s.row)"/></label><button v-else class="link-action" @click="emit('view',s.row.application_id)">查看</button></div></template></el-table-column>
    </el-table>
   </el-tab-pane>
  </el-tabs>
 </div>
 <el-dialog v-model="dialog" :title="mode==='create'?'新增岗位申请':'编辑候选人与申请'" width="min(560px, 95vw)">
  <div class="management-form">
   <template v-if="mode==='create'"><label>已有候选人（可选）<el-select v-model="form.candidate_id" clearable filterable placeholder="选择已有候选人，或在下方新建"><el-option v-for="c in candidates" :key="c.id" :label="`${c.name} · ${c.id.slice(0,8)}`" :value="c.id"/></el-select></label><label v-if="!form.candidate_id">新候选人姓名<el-input v-model="form.candidate_name" maxlength="100"/></label><label>应聘岗位<el-select v-model="form.position_id" filterable allow-create default-first-option placeholder="选择岗位，或输入新岗位名称"><el-option v-for="p in positions" :key="p.id" :label="p.title" :value="p.id"/></el-select></label></template>
   <label v-else>候选人姓名<el-input v-model="form.name" maxlength="100"/></label>
   <template v-if="mode==='edit'||!form.candidate_id"><label>电话<el-input v-model="form.phone" maxlength="100"/></label><label>邮箱<el-input v-model="form.email" maxlength="255"/></label><label>学历<el-input v-model="form.education" maxlength="120"/></label><label>技能<el-input v-model="form.skills" type="textarea" :rows="2"/></label><label>工作年限<el-input-number v-model="form.work_years" :min="0" :max="80"/></label></template>
   <label>负责人<el-input v-model="form.owner" maxlength="100"/></label>
   <p v-if="mode==='edit'" class="management-note">候选人资料修改会反映在该候选人的所有申请中。更换岗位请新建申请。</p>
  </div><template #footer><button class="primary-button" :disabled="busy" @click="save">{{busy?'保存中…':'保存'}}</button></template>
 </el-dialog>
 <el-dialog v-model="resumeDialog" :title="`维护简历 · ${resumeApp?.candidate_name||''}`" width="min(600px, 95vw)">
  <div class="management-form"><p class="management-note">简历归属于候选人，同一候选人的所有申请均可查看。可上传 TXT / PDF / DOCX，或直接填写文字并保存为简历。</p><label class="plain-button file-picker">上传已有简历 TXT / PDF / DOCX<input type="file" accept=".txt,.pdf,.docx" :disabled="busy" @change="uploadResume"/></label><label>人工填写简历内容<el-input v-model="resumeText" type="textarea" :rows="9" maxlength="100000" placeholder="填写教育经历、工作经历、项目经验和技能等"/></label></div>
  <template #footer><button class="primary-button" :disabled="busy" @click="saveManualResume">{{busy?'保存中…':'保存文字简历'}}</button></template>
 </el-dialog>
 <el-dialog v-model="screeningDialog" :title="`人工初筛 · ${screeningApp?.candidate_name||''}`" width="min(560px, 95vw)">
  <div class="management-form"><label>初筛评价<el-input v-model="screeningForm.evaluation" type="textarea" :rows="4" placeholder="填写岗位匹配情况及评价"/></label><label>处理结果<el-radio-group v-model="screeningForm.decision"><el-radio value="PENDING">待定</el-radio><el-radio value="REJECT">淘汰</el-radio><el-radio value="INTERVIEW">进入一面</el-radio></el-radio-group></label><p class="management-note">选择进入一面后，再安排面试时间和面试官。</p></div>
  <template #footer><button class="primary-button" :disabled="busy" @click="saveScreening">确认初筛</button></template>
 </el-dialog>
 <el-dialog v-model="interviewDialog" :title="interviewMode==='edit'?'编辑面试资料':'安排面试 / 记录反馈'" width="min(560px, 95vw)">
  <div class="management-form">
   <template v-if="interviewMode==='action'"><label>关联申请<el-select v-model="interviewForm.application_id" filterable placeholder="请选择申请"><el-option v-for="a in props.rows" :key="a.id" :label="`${a.candidate_name} · ${a.position} · ${a.stage_label}`" :value="a.id"/></el-select></label><label>操作<el-select v-model="interviewForm.action"><el-option label="安排面试" value="schedule"/><el-option label="记录反馈" value="feedback"/></el-select></label><label>面试轮次<el-select v-model="interviewForm.round_no"><el-option v-for="n in [1,2,3]" :key="n" :label="`${n} 面`" :value="n"/></el-select></label></template>
   <template v-if="interviewMode==='edit'||interviewForm.action==='schedule'"><label>面试时间<DateTimePicker v-model="interviewForm.scheduled_at"/></label><label>面试官<el-input v-model="interviewForm.interviewer" maxlength="100"/></label></template>
   <template v-if="(interviewMode==='action'&&interviewForm.action==='feedback')||(interviewMode==='edit'&&interviewCompleted)"><label>面试评价<el-input v-model="interviewForm.evaluation" type="textarea" :rows="3"/></label></template>
   <label v-if="interviewMode==='action'&&interviewForm.action==='feedback'">面试结论<el-select v-model="interviewForm.decision"><el-option label="待定" value="PENDING"/><el-option label="通过" value="PASS"/><el-option label="未通过" value="REJECT"/></el-select></label>
   <p class="management-note">安排与反馈会检查当前阶段，并生成招聘事件。编辑资料不会自动改变结论或阶段。</p>
  </div><template #footer><button class="primary-button" :disabled="busy" @click="saveInterview">{{busy?'保存中…':'保存'}}</button></template>
 </el-dialog>
</template>
