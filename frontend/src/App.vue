<script setup lang="ts">
import {computed, nextTick, onMounted, onBeforeUnmount, ref, watch} from 'vue'
import axios from 'axios'
import {init as initChart, use as useChart} from 'echarts/core'
import type {ECharts} from 'echarts/core'
import {BarChart} from 'echarts/charts'
import {GridComponent, TooltipComponent} from 'echarts/components'
import {CanvasRenderer} from 'echarts/renderers'
import RecruitmentTable from './RecruitmentTable.vue'
import DateTimePicker from './DateTimePicker.vue'
import ModelSettingsDialog from './components/ModelSettingsDialog.vue'
import ResumeAssessments from './ResumeAssessments.vue'
import type {AppRow, InterviewScore, InterviewSummary, ModelSettings} from './types/recruitment'
import {errorMessage as safeError} from './utils/errors'
import {modelConfig, modelConfigComplete} from './utils/model'
import { ElMessage, ElMessageBox } from 'element-plus'
import { LayoutDashboard, MessageSquareText, Users, ClipboardCheck, GitBranch,
  Sparkles, Bot, Send, Paperclip, RefreshCw, ChevronRight, CalendarDays,
  Clock3, CheckCircle2, AlertTriangle, FileText, Database, CloudUpload,
  ArrowRight, BriefcaseBusiness, Activity, ShieldCheck, X, RotateCcw, Settings2 } from 'lucide-vue-next'

type DemoExample = {application_id:string;stage:string;text:string}
type ReviewRow = {id:string;reason:string;application_id:string|null;proposal:any;status:string;created_at:string}
type Stats = {total:number;interviewing:number;offer_accepted:number;hired:number;pending_reviews:number;pending_sync:number;interviews_completed:number;stages:{stage:string;name:string;count:number}[]}
type InterviewNotes = {id:string;filename:string;characters:number;text:string;model:string;created_at:string;summary:InterviewSummary;review:{decision:string;status:string;evaluation:InterviewSummary}|null}
type InterviewRow = {id:string;round_no:number;interviewer:string|null;scheduled_at:string|null;status:string;result:string;evaluation:string|null;transcript:InterviewNotes|null}
type Detail = {application:AppRow;candidate:{name:string;phone:string|null;email:string|null;education:string|null;skills:string|null;work_years:number|null};resumes:{id:string;filename:string;uploaded_at:string;text:string}[];interviews:InterviewRow[];events:any[]}
type ChatItem = {id:string;content:string;file_id:string|null;status:string;result:any;created_at:string}

const nav = [
 {id:'overview',label:'招聘驾驶舱',icon:LayoutDashboard},
 {id:'chat',label:'AI 招聘助手',icon:MessageSquareText},
 {id:'resume',label:'简历评估',icon:FileText},
 {id:'candidates',label:'候选人管理',icon:Users},
 {id:'reviews',label:'人工审核中心',icon:ClipboardCheck},
 {id:'sync',label:'事件同步状态',icon:GitBranch},
]
const active=ref('overview')
const rows=ref<AppRow[]>([])
const reviews=ref<ReviewRow[]>([])
const messages=ref<ChatItem[]>([])
const demoExamples=ref<DemoExample[]>([])
const syncing=ref<any[]>([])
const stats=ref<Stats|null>(null)
const health=ref<{ok:boolean;model_mode:string;model_name:string;sync_configured:boolean}|null>(null)
const showModelSettings=ref(false)
const modelSettings=ref<ModelSettings>({mode:'demo',model:'',base_url:'',api_key:''})
const modelStatus=computed(()=>modelSettings.value.mode==='demo'?'规则演示 · 无需模型':modelSettings.value.mode==='custom'?`${modelSettings.value.model||'自定义模型'} · 自行配置`:health.value?.model_mode==='model'?'服务器模型 · 已配置':'服务器规则演示')
const loading=ref(false)
const sending=ref(false)
const messageText=ref('')
const selectedApp=ref<string>('')
const uploaded=ref<{id:string;filename:string;characters:number}|null>(null)
const uploadBusy=ref(false)
const detail=ref<Detail|null>(null)
const showDetail=ref(false)
const transcriptBusy=ref<string|null>(null)
const interviewReview=ref<{interviewId:string;transcriptId:string}|null>(null)
const interviewReviewBusy=ref(false)
const interviewReviewForm=ref({candidate_name:'',position:'',round_no:1,interviewer:'',interview_time:'',duration:'',summary:'',topics:'',performance:'',scores:[] as InterviewScore[],strengths:'',concerns:'',follow_ups:'',suggestions:'',decision:''})
const durationOptions=Array.from({length:480},(_,i)=>`${i+1}分钟`)
const edits=ref<Record<string,{intent:string;application_id:string;candidate_name:string;position:string;scheduled_at:string;round_no:number|null;decision:string;evaluation:string;interviewer:string;next_stage:string}>>({})
const chartDom=ref<HTMLDivElement|null>(null)
const conversationFeed=ref<HTMLDivElement|null>(null)
useChart([BarChart, GridComponent, TooltipComponent, CanvasRenderer])
let chart:ECharts|null=null
let refreshGeneration=0
const lastSync=ref('')
const stages=['SCREENING','ROUND1_PENDING','ROUND1_SCHEDULED','ROUND1_FEEDBACK','ROUND2_PENDING','ROUND2_SCHEDULED','ROUND2_FEEDBACK','ROUND3_PENDING','ROUND3_SCHEDULED','ROUND3_FEEDBACK','OFFER_PENDING','OFFER_ACCEPTED','HIRED','REJECTED','WITHDRAWN']
const funnelStages=['SCREENING','ROUND1_PENDING','ROUND1_SCHEDULED','ROUND1_FEEDBACK','ROUND2_PENDING','ROUND2_SCHEDULED','ROUND2_FEEDBACK','ROUND3_PENDING','ROUND3_SCHEDULED','ROUND3_FEEDBACK','OFFER_PENDING','OFFER_ACCEPTED','HIRED']
const title=computed(()=>nav.find(x=>x.id===active.value)?.label ?? '招聘管理')
const stageChip=(s:string)=>['HIRED','OFFER_ACCEPTED'].includes(s)?'good':['REJECTED','WITHDRAWN'].includes(s)?'muted':s==='SCREENING'?'basic':'blue'
const short=(s:string|undefined, n=8)=>(s||'').slice(0,n)
const fmt=(s:string|undefined)=>s?s.replace('T',' ').slice(0,16):'—'
const activeCount=computed(()=>stats.value?.stages.filter(s=>!['REJECTED','WITHDRAWN','HIRED'].includes(s.stage)).reduce((a,b)=>a+b.count,0)||0)
watch([active,()=>messages.value[0]?.id,()=>messages.value[0]?.status],([view])=>{
 if(view==='chat'&&conversationFeed.value)conversationFeed.value.scrollTop=conversationFeed.value.scrollHeight
},{flush:'post'})
function aiConfig(){return modelConfig(modelSettings.value)}
function validModelSettings(){
 const s=modelSettings.value
 if(!modelConfigComplete(s)){ElMessage.warning('请填写模型名称和兼容接口地址');showModelSettings.value=true;return false}
 return true
}

async function refresh(){
 const generation=++refreshGeneration
 loading.value=true
 try{
  const results=await Promise.allSettled([
   axios.get('/api/v1/applications'), axios.get('/api/v1/stats/overview'),
   axios.get('/api/v1/reviews'), axios.get('/api/v1/messages'),
   axios.get('/api/v1/sync/jobs'), axios.get('/api/v1/health'), axios.get('/api/v1/demo/examples')
  ])
  if(generation!==refreshGeneration)return
  const [a,b,c,d,e,f,g]=results
  if(a.status==='fulfilled')rows.value=a.value.data
  if(b.status==='fulfilled')stats.value=b.value.data
  if(c.status==='fulfilled')reviews.value=c.value.data
  if(d.status==='fulfilled')messages.value=d.value.data
  if(e.status==='fulfilled')syncing.value=e.value.data
  if(f.status==='fulfilled')health.value=f.value.data
  if(g.status==='fulfilled')demoExamples.value=g.value.data
  const failures=results.filter(result=>result.status==='rejected').length
  if(failures)ElMessage.warning(`${failures} 项数据刷新失败，请稍后重试`)
  lastSync.value=new Date().toLocaleTimeString('zh-CN')
  if(!stats.value?.total && chart){chart.dispose();chart=null}
  if(active.value==='overview') await nextTick().then(drawChart)
 }catch(e){if(generation===refreshGeneration)ElMessage.error(safeError(e))}finally{if(generation===refreshGeneration)loading.value=false}
}
async function switchView(v:string){
 if(active.value==='overview'&&v!=='overview'&&chart){chart.dispose();chart=null}
 active.value=v
 if(v==='overview') await nextTick().then(drawChart)
}
function drawChart(){
 if(!chartDom.value || !stats.value || active.value!=='overview')return
 if(!chart)chart=initChart(chartDom.value)
 const ss=stats.value.stages.filter(s=>s.count>0)
 chart.setOption({
  tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},
  grid:{left:12,right:24,top:24,bottom:14,containLabel:true},
  xAxis:{type:'value',axisLine:{show:false},axisTick:{show:false},splitLine:{lineStyle:{color:'#edf0f5'}},axisLabel:{color:'#9aa4b2'}},
  yAxis:{type:'category',inverse:true,data:ss.map(x=>x.name),axisLine:{show:false},axisTick:{show:false},axisLabel:{color:'#596679',fontSize:12}},
  series:[{type:'bar',data:ss.map(x=>x.count),barWidth:19,itemStyle:{color:'#4779ce',borderRadius:[0,5,5,0]},label:{show:true,position:'right',color:'#384a63',fontWeight:600}}]
 },true)
 chart.resize()
}
async function onFile(event:Event){
 const input=event.target as HTMLInputElement
 if(!input.files?.length)return
 const f=input.files[0]
 if(!/\.(txt|pdf|docx)$/i.test(f.name)){ElMessage.warning('仅支持 TXT / PDF / DOCX');input.value='';return}
 const data=new FormData();data.append('file',f)
 uploadBusy.value=true
 try{
  const resp=await axios.post('/api/v1/files',data);uploaded.value=resp.data
  const hadSelection=!!selectedApp.value;selectedApp.value=''
  ElMessage.success(hadSelection?'已提取简历文字并清除原关联；更新已有申请请重新选择':'已提取简历文字，请发送以生成评估')
 }
 catch(e){ElMessage.error(safeError(e))}finally{uploadBusy.value=false;input.value=''}
}
async function send(){
 if(sending.value)return
 if(!messageText.value.trim()&&!uploaded.value){ElMessage.warning('请填写消息或上传简历');return}
 if(!validModelSettings())return
 sending.value=true
 try{
  if(uploaded.value){
   await axios.post('/api/v1/resume-assessments',{file_id:uploaded.value.id,application_id:selectedApp.value||null,context:messageText.value.trim(),ai_config:aiConfig()})
   messageText.value='';uploaded.value=null;selectedApp.value='';active.value='resume'
   ElMessage.success('简历参考意见已生成，请核对并选择处理结果')
   await refresh();return
  }
  const p={source:'web',external_message_id:crypto.randomUUID(),sender_id:'hr-demo',content:messageText.value.trim(),
   application_id:selectedApp.value||null,ai_config:aiConfig()}
  const {data}=await axios.post('/api/v1/messages',p)
  if(data.status==='pending_review')ElMessage.warning('已转人工审核：'+data.reason)
  else ElMessage.success(data.detail||'处理成功')
  messageText.value='';uploaded.value=null
  await refresh()
 }catch(e){ElMessage.error(safeError(e));await refresh()}finally{sending.value=false}
}
async function viewDetail(id:string){
 try{const {data}=await axios.get('/api/v1/applications/'+id);detail.value=data;showDetail.value=true}
 catch(e){ElMessage.error(safeError(e))}
}
async function uploadTranscriptFile(file:File, interviewId:string, applicationId:string){
 if(transcriptBusy.value)return
 if(!/\.(txt|pdf|docx)$/i.test(file.name)){ElMessage.warning('仅支持 TXT / PDF / DOCX');return}
 if(!validModelSettings())return
 const data=new FormData();data.append('file',file)
 const settings=modelSettings.value
 data.append('ai_mode',settings.mode)
 if(settings.mode==='custom'){
  data.append('ai_model',settings.model.trim());data.append('ai_base_url',settings.base_url.trim())
  data.append('ai_api_key',settings.api_key)
 }
 transcriptBusy.value=interviewId
 try{
  await axios.post(`/api/v1/interviews/${interviewId}/transcripts`,data)
  ElMessage.success(settings.mode==='demo'?'已生成规则演示摘要':'面试文字已上传，总结已生成')
  await viewDetail(applicationId)
 }catch(e){ElMessage.error(safeError(e))}finally{transcriptBusy.value=null}
}
async function uploadTranscript(event:Event, interviewId:string, applicationId:string){
 const input=event.target as HTMLInputElement
 const file=input.files?.[0]
 if(file)await uploadTranscriptFile(file,interviewId,applicationId)
 input.value=''
}
function openInterviewReview(iv:InterviewRow){
 if(!iv.transcript||!detail.value)return
 const x=iv.transcript.review?.evaluation||iv.transcript.summary
 interviewReview.value={interviewId:iv.id,transcriptId:iv.transcript.id}
 interviewReviewForm.value={candidate_name:x.candidate_name||detail.value.candidate.name,position:x.position||detail.value.application.position,
  round_no:x.round_no||iv.round_no,interviewer:x.interviewer||iv.interviewer||'',interview_time:x.interview_time||'',duration:x.duration||'',summary:x.summary,
  topics:(x.topics||[]).join('\n'),performance:(x.performance||[]).join('\n'),scores:(x.scores||[]).map(score=>({...score})),strengths:(x.strengths||[]).join('\n'),concerns:(x.concerns||[]).join('\n'),follow_ups:(x.follow_ups||[]).join('\n'),suggestions:(x.suggestions||[]).join('\n'),decision:''}
}
async function confirmInterviewReview(){
 const f=interviewReviewForm.value
 if(!interviewReview.value||interviewReviewBusy.value)return
 if(!f.decision||!f.summary.trim()){ElMessage.warning('请填写面试总结并选择处理结果');return}
 if(f.scores.some(s=>!s.dimension.trim()||(s.score!=null&&!s.evidence.trim()))){ElMessage.warning('请填写评分维度；有分数时必须填写依据');return}
 const lines=(s:string)=>s.split('\n').map(x=>x.trim()).filter(Boolean)
 interviewReviewBusy.value=true
 try{
  await axios.post(`/api/v1/interviews/${interviewReview.value.interviewId}/transcripts/${interviewReview.value.transcriptId}/decision`,{
   decision:f.decision,evaluation:{candidate_name:f.candidate_name||null,position:f.position||null,round_no:f.round_no,interviewer:f.interviewer||null,interview_time:f.interview_time||null,duration:f.duration||null,summary:f.summary.trim(),topics:lines(f.topics),performance:lines(f.performance),scores:f.scores,strengths:lines(f.strengths),concerns:lines(f.concerns),follow_ups:lines(f.follow_ups),suggestions:lines(f.suggestions)}})
  interviewReview.value=null;ElMessage.success('已保存面试官确认结果')
  if(detail.value)await viewDetail(detail.value.application.id)
  await refresh()
 }catch(e){ElMessage.error(safeError(e))}finally{interviewReviewBusy.value=false}
}
function editOf(r:ReviewRow){
 if(!edits.value[r.id]) edits.value[r.id]={intent:r.proposal?.intent||'UNKNOWN',application_id:r.proposal?.application_id||r.application_id||'',
  candidate_name:r.proposal?.candidate_name||'',position:r.proposal?.position||'',
  scheduled_at:r.proposal?.scheduled_at||'',round_no:r.proposal?.round_no||null,
  decision:r.proposal?.decision||'PENDING',evaluation:r.proposal?.evaluation||'',interviewer:r.proposal?.interviewer||'',next_stage:r.proposal?.next_stage||''}
 return edits.value[r.id]
}
async function decide(r:ReviewRow,action:'approve'|'reject'){
 try{
  if(action==='reject') await ElMessageBox.confirm('确认拒绝此次变更？原始消息和审核记录将保留。','审核确认',{type:'warning'})
  const x=editOf(r)
  const payload={action,intent:x.intent,application_id:x.application_id||null,candidate_name:x.candidate_name||null,
   position:x.position||null,round_no:x.round_no,scheduled_at:x.scheduled_at||null,decision:x.decision||null,
   evaluation:x.evaluation||null,interviewer:x.interviewer||null,next_stage:x.next_stage||null}
  const {data}=await axios.post(`/api/v1/reviews/${r.id}/resolve`,payload)
  ElMessage.success(data.detail||'审核成功');await refresh()
 }catch(e:any){if(e!=='cancel')ElMessage.error(safeError(e))}
}
async function retry(id:string){try{await axios.post('/api/v1/sync/jobs/'+id+'/retry');ElMessage.success('任务已重新入队');await refresh()}catch(e){ElMessage.error(safeError(e))}}
function quick(example:DemoExample){
 const row=rows.value.find(r=>r.id===example.application_id)
 if(!row){ElMessage.warning('演示申请不存在，请重启后端补齐初始化数据');return}
 if(row.stage!==example.stage){ElMessage.warning(`当前为${row.stage_label}，请按顺序选择适用的演示步骤`);return}
 selectedApp.value=row.id;messageText.value=example.text;active.value='chat'
}
function resize(){chart?.resize()}
onMounted(()=>{refresh();window.addEventListener('resize',resize)})
onBeforeUnmount(()=>{refreshGeneration++;chart?.dispose();window.removeEventListener('resize',resize)})
</script>

<template>
 <div class="shell">
  <aside class="sidebar">
   <div class="brand"><div class="brand-logo"><Sparkles :size="21" stroke-width="2.4"/></div><div class="brand-copy"><strong>HireFlow <span>AI</span></strong><small>智能招聘运营平台</small></div></div>
   <div class="workspace-chip"><div class="work-icon"><BriefcaseBusiness :size="16"/></div><div><b>招聘管理工作台</b><small>演示工作空间</small></div><ChevronRight :size="14" class="push"/></div>
   <div class="section-label">工作空间</div>
   <nav class="menu"><button v-for="item in nav" :key="item.id" :class="['navitem',{chosen:active===item.id}]" @click="switchView(item.id)"><component :is="item.icon" :size="18" stroke-width="1.9"/><span>{{item.label}}</span><span v-if="item.id==='reviews' && stats?.pending_reviews" class="nav-count">{{stats.pending_reviews}}</span></button></nav>
   <div class="sidebar-end"><div class="ai-status"><span class="pulse"></span><div><b>处理模式</b><small>{{modelStatus}}</small></div></div><div class="profile"><div class="avatar">HR</div><div><b>招聘管理员</b><small>本地演示账户</small></div><span class="push user-indicator"></span></div></div>
  </aside>
  <main class="main">
   <header class="topbar"><div class="breadcrumbs">HireFlow AI <ChevronRight :size="14"/> <b>{{title}}</b></div><div class="topbar-actions"><button class="model-settings-button" @click="showModelSettings=true"><Settings2 :size="16"/> 模型设置</button><span class="header-time">上次刷新 {{lastSync||'—'}}</span><button class="icon-button" title="刷新数据" @click="refresh"><RefreshCw :size="17" :class="{spin:loading}"/></button><span class="header-divider"></span><div class="avatar mini">HR</div></div></header>
   <div class="content">
    <template v-if="active==='overview'">
      <div class="page-intro intro-inline"><div><span class="eyebrow"><span class="eyebrow-dot"></span> RECRUITMENT OVERVIEW</span><h1>招聘数据驾驶舱</h1><p>从简历到 Offer，让每一个招聘节点都清晰可见。</p></div><button class="primary-button" @click="switchView('chat')"><Sparkles :size="17"/> 开始 AI 招聘记录 <ArrowRight :size="16"/></button></div>
      <div class="metric-grid">
       <div class="metric"><div class="metric-head"><span>招聘申请总数</span><div class="metric-icon indigo"><Users :size="19"/></div></div><div class="metric-value">{{stats?.total ?? '—'}}<span>人次</span></div><small>覆盖所有招聘岗位申请</small></div>
       <div class="metric"><div class="metric-head"><span>当前进行中</span><div class="metric-icon blue"><Activity :size="19"/></div></div><div class="metric-value">{{activeCount}}<span>人次</span></div><small>未结束的招聘流程</small></div>
       <div class="metric"><div class="metric-head"><span>待人工审核</span><div class="metric-icon orange"><AlertTriangle :size="19"/></div></div><div class="metric-value">{{stats?.pending_reviews ?? '—'}}<span>条</span></div><small>需要 HR 判断与确认</small></div>
       <div class="metric"><div class="metric-head"><span>Offer 已接受</span><div class="metric-icon green"><CheckCircle2 :size="19"/></div></div><div class="metric-value">{{stats?.offer_accepted ?? '—'}}<span>人次</span></div><small>累计录用流程进展</small></div>
      </div>
      <div class="overview-layout"><div class="panel graph-panel"><div class="panel-head"><div><h3>招聘阶段分布</h3><p>按岗位申请当前阶段去重统计</p></div><div class="panel-indicator"><span></span> 实时数据</div></div><div v-if="stats?.total" ref="chartDom" class="chart"></div><div v-else class="empty-illustration"><LayoutDashboard :size="43"/><b>还没有招聘数据</b><span>上传第一份模拟简历后，这里将自动显示招聘进度统计</span><button class="text-button" @click="switchView('chat')">去体验 AI 招聘助手 →</button></div></div>
       <div class="panel side-panel"><div class="panel-head"><div><h3>流程运行状态</h3><p>系统实时统计</p></div></div><div class="system-stat"><span class="sys-icon sky"><GitBranch :size="19"/></span><div><b>已完成面试</b><small>多轮面试结果累计</small></div><strong>{{stats?.interviews_completed ?? 0}}</strong></div><div class="system-stat"><span class="sys-icon amber"><ClipboardCheck :size="19"/></span><div><b>待审核操作</b><small>避免错误流程推进</small></div><strong>{{stats?.pending_reviews ?? 0}}</strong></div><div class="system-stat"><span class="sys-icon purple"><CloudUpload :size="19"/></span><div><b>待同步事件</b><small>腾讯文档事件流水</small></div><strong>{{stats?.pending_sync ?? 0}}</strong></div><div class="mini-notice"><ShieldCheck :size="18"/><span>招聘决定由 HR 作出。AI 只负责理解信息、记录并校验流程。</span></div></div></div>
      <div class="panel table-panel"><div class="panel-head"><div><h3>最近招聘进展</h3><p>候选人当前阶段与最新更新时间</p></div><button class="text-button" @click="switchView('candidates')">查看全部 <ChevronRight :size="15"/></button></div><el-table :data="rows.slice(0,6)" class="clean-table" empty-text="暂无候选人数据，先去 AI 助手上传简历" @row-click="(r:any)=>viewDetail(r.id)"><el-table-column prop="candidate_name" label="候选人" min-width="135"/><el-table-column prop="position" label="应聘岗位" min-width="185"/><el-table-column label="当前阶段" min-width="160"><template #default="s"><span :class="['stage-pill',stageChip(s.row.stage)]">{{s.row.stage_label}}</span></template></el-table-column><el-table-column label="更新时间" min-width="150"><template #default="s">{{fmt(s.row.updated_at)}}</template></el-table-column><el-table-column label="详情" width="75"><template #default><ChevronRight :size="15"/></template></el-table-column></el-table></div>
    </template>
    <template v-else-if="active==='chat'">
     <div class="page-intro"><span class="eyebrow"><span class="eyebrow-dot"></span> AI WORKSPACE</span><h1>AI 招聘助手 <span class="title-star">✦</span></h1><p>像在企业微信中聊天一样记录招聘进展，AI 将自动识别和更新候选人数据。</p></div>
     <div class="chat-layout"><div class="panel conversation"><div class="conversation-head"><div class="bot-avatar"><Bot :size="22"/></div><div><h3>HireFlow 智能助手 <span class="online-dot"></span></h3><p>{{modelStatus}} · LangGraph 工作流</p></div><div class="push connection"><span></span> 已连接</div></div>
       <div ref="conversationFeed" class="conversation-feed"><div class="welcome"><div class="welcome-orb"><Sparkles :size="27"/></div><h2>你好，我是 HireFlow AI</h2><p>上传简历、记录面试评价、更新进度。<br/>我会将招聘过程转化为可追踪的数据。</p><div class="welcome-chips"><span>✦ 简历评估与确认</span><span>✦ 多轮面试跟踪</span><span>✦ 异常人工审核</span></div></div>
        <div v-for="m in [...messages].reverse().slice(-10)" :key="m.id" class="message-group"><div class="user-bubble">{{m.content||'📎 已上传简历文件'}}<small>{{fmt(m.created_at)}}</small></div><div :class="['assistant-reply',m.status==='failed'?'is-error':'']"><span class="assistant-icon"><Bot :size="15"/></span><div><b>{{m.status==='applied'?'更新成功':m.status==='pending_review'?'等待人工审核':m.status==='failed'?'处理失败':m.status==='rejected'?'审核已拒绝':'处理中'}}</b><p>{{m.result?.detail||m.result?.reason||m.result?.error||'正在分析招聘消息...'}}</p></div></div></div>
       </div>
       <div class="compose-area"><div class="context-select"><span><Database :size="15"/> 关联招聘申请</span><el-select v-model="selectedApp" clearable filterable placeholder="新简历建档时不选择；进度更新请选申请" size="small"><el-option v-for="r in rows" :key="r.id" :label="`${r.candidate_name} · ${r.position} · ${r.stage_label}`" :value="r.id"/></el-select></div>
       <div v-if="uploaded" class="upload-tag"><FileText :size="15"/><span>{{uploaded.filename}} · {{uploaded.characters}} 字</span><button @click="uploaded=null"><X :size="14"/></button></div>
       <textarea v-model="messageText" rows="3" placeholder="输入招聘进度，例如：一面结束，Python 基础扎实，一面通过，安排二面..." @keydown.ctrl.enter.prevent="send"></textarea>
       <div class="compose-bottom"><label class="file-picker"><Paperclip :size="17"/><span>{{uploadBusy?'正在解析...':'上传简历 TXT / PDF / DOCX'}}</span><input type="file" accept=".txt,.pdf,.docx" :disabled="uploadBusy||sending" @change="onFile"/></label><span class="compose-hint">Ctrl + Enter 发送</span><button class="primary-button send-button" :disabled="sending||uploadBusy" @click="send"><Send :size="16"/> {{sending?'处理中...':'发送消息'}}</button></div></div>
      </div>
      <aside class="chat-aside"><div class="panel helper-panel"><div class="panel-head"><div><h3>快捷演示</h3><p>虚构候选人林知远 · 按顺序选择，自动关联申请</p></div></div><button v-for="(q,i) in demoExamples" :key="i" class="example-button" @click="quick(q)"><span class="example-num">{{i+1}}</span><span>{{q.text}}</span><ArrowRight :size="14"/></button></div><div class="info-card"><ShieldCheck :size="23"/><b>数据校验保护</b><p>缺少时间、候选人匹配冲突、错误面试轮次不会直接写入，将自动进入人工审核。</p></div></aside></div>
    </template>
    <template v-else-if="active==='resume'"><ResumeAssessments :rows="rows" @refresh="refresh" @upload="switchView('chat')"/></template>
    <template v-else-if="active==='candidates'"><RecruitmentTable :rows="rows" :transcript-busy="!!transcriptBusy" @refresh="refresh" @view="viewDetail" @upload-transcript="uploadTranscriptFile"/></template>
    <template v-else-if="active==='reviews'">
     <div class="page-intro"><span class="eyebrow">HUMAN-IN-THE-LOOP</span><h1>人工审核中心</h1><p>对于身份无法匹配、时间不明确或流程跳转异常的消息，由 HR 确认后再执行。</p></div>
     <div v-if="!reviews.length" class="panel blank-state"><ShieldCheck :size="45"/><h3>暂无审核任务</h3><p>当 AI 遇到无法安全执行的消息时，会自动在这里创建待审核任务。</p></div>
     <div v-for="r in reviews" :key="r.id" class="panel review-card"><div class="review-header"><span :class="['stage-pill',r.status==='pending'?'orange':'good']">{{r.status==='pending'?'待处理':r.status==='approved'?'已批准':'已拒绝'}}</span><small>{{fmt(r.created_at)}} · {{short(r.id)}}</small></div><h3>{{r.reason}}</h3><p class="review-original">AI 识别：{{r.proposal?.intent}} · {{r.proposal?.candidate_name||'候选人待确认'}} · {{r.proposal?.position||'岗位待确认'}}</p><div v-if="r.status==='pending'" class="review-edit"><div class="edit-grid"><label>招聘操作<el-select v-model="editOf(r).intent" placeholder="请选择要执行的操作"><el-option label="请选择" value="UNKNOWN" disabled/><el-option v-if="r.proposal?.intent==='RESUME_RECEIVED'" label="接收简历" value="RESUME_RECEIVED"/><el-option label="初筛评价" value="HR_EVALUATION"/><el-option label="安排面试" value="INTERVIEW_SCHEDULE"/><el-option label="记录面试反馈" value="INTERVIEW_FEEDBACK"/><el-option label="更新招聘状态" value="STATUS_UPDATE"/><el-option label="查询招聘状态" value="INFORMATION_QUERY"/></el-select></label><label>关联申请<el-select v-model="editOf(r).application_id" clearable filterable placeholder="新申请请清空，已有申请请选择" size="default"><el-option v-for="a in rows" :key="a.id" :label="`${a.candidate_name} / ${a.position}`" :value="a.id"/></el-select><small v-if="r.proposal?.intent==='RESUME_RECEIVED'">新建申请请清空；同名或多岗位时请选择正确申请。</small></label><label>候选人姓名<el-input v-model="editOf(r).candidate_name" placeholder="候选人姓名"/></label><label>岗位名称<el-input v-model="editOf(r).position" placeholder="岗位"/></label><label>面试轮次<el-select v-model="editOf(r).round_no" clearable placeholder="可选"><el-option v-for="n in [1,2,3]" :key="n" :label="`${n} 面`" :value="n"/></el-select></label><label>准确日期时间<DateTimePicker v-model="editOf(r).scheduled_at"/></label><label>面试结论<el-select v-model="editOf(r).decision"><el-option label="待定" value="PENDING"/><el-option label="通过" value="PASS"/><el-option label="淘汰" value="REJECT"/></el-select></label><label v-if="['HR_EVALUATION','INTERVIEW_FEEDBACK'].includes(editOf(r).intent)">评价内容<el-input v-model="editOf(r).evaluation" type="textarea" placeholder="填写人工确认的评价"/></label><label v-if="editOf(r).intent==='INTERVIEW_SCHEDULE'">面试官<el-input v-model="editOf(r).interviewer" placeholder="面试官姓名"/></label><label v-if="editOf(r).intent==='STATUS_UPDATE'">目标阶段<el-select v-model="editOf(r).next_stage" placeholder="选择目标阶段"><el-option label="Offer 待处理" value="OFFER_PENDING"/><el-option label="Offer 已接受" value="OFFER_ACCEPTED"/><el-option label="已入职" value="HIRED"/><el-option label="已淘汰" value="REJECTED"/><el-option label="已退出" value="WITHDRAWN"/></el-select></label></div><p v-if="editOf(r).intent==='UNKNOWN'" class="review-original">请选择具体招聘操作，再填写相关信息。面试全文请从候选人管理的待进行面试上传。</p><div class="review-actions"><button class="plain-button" @click="decide(r,'reject')">拒绝操作</button><button class="primary-button" @click="decide(r,'approve')"><CheckCircle2 :size="17"/> 确认并执行</button></div></div></div>
    </template>
    <template v-else-if="active==='sync'">
     <div class="page-intro"><span class="eyebrow">EVENT SYNCHRONIZATION</span><h1>腾讯文档同步</h1><p>所有招聘变更先持久化，再通过异步事件队列同步到腾讯在线表格。</p></div>
     <div :class="['sync-banner',health?.sync_configured?'ready':'unconfigured']"><CloudUpload :size="25"/><div><b>{{health?.sync_configured?'HiFlow Webhook 已配置':'尚未配置 HiFlow Webhook'}}</b><p>{{health?.sync_configured?'事件队列会定期尝试发送，失败将退避重试。':'请在 .env 配置文件中设置 HIFLOW_WEBHOOK_URL，重启后端启用真实同步。'}}</p></div></div>
     <div class="panel table-panel"><div class="panel-head"><div><h3>事件同步任务</h3><p>仅同步事件流水，不反向覆盖招聘数据</p></div><span class="count-pill">{{syncing.length}} 条记录</span></div><el-table :data="syncing" class="clean-table" empty-text="暂无招聘事件同步任务"><el-table-column label="事件 ID" min-width="155"><template #default="s"><span class="mono">{{short(s.row.event_id,12)}}</span></template></el-table-column><el-table-column label="同步状态" min-width="135"><template #default="s"><span :class="['stage-pill',s.row.status==='success'?'good':s.row.status==='failed'?'orange':'basic']">{{s.row.status==='success'?'已同步':s.row.status==='failed'?'失败':'待同步'}}</span></template></el-table-column><el-table-column prop="retry_count" label="重试次数" width="100"/><el-table-column label="最近错误" min-width="220"><template #default="s"><span class="ellipsis">{{s.row.last_error||'—'}}</span></template></el-table-column><el-table-column label="操作" width="100"><template #default="s"><button v-if="s.row.status!=='success'" class="link-action" @click="retry(s.row.id)"><RotateCcw :size="13"/> 重新入队</button></template></el-table-column></el-table></div>
    </template>
   </div>
  </main>
  <ModelSettingsDialog v-model:visible="showModelSettings" v-model:settings="modelSettings" :server-mode="health?.model_mode"/>
  <el-dialog :model-value="!!interviewReview" title="核对面试评估" width="min(650px, 95vw)" @close="interviewReview=null">
   <div class="management-form interview-review-form">
    <p class="management-note">AI 参考意见可修改，候选人、岗位和轮次须与关联面试一致。确认后按所选结果更新流程；三面推进至 Offer 待处理。</p>
    <div class="edit-grid"><label>候选人<el-input v-model="interviewReviewForm.candidate_name"/></label><label>岗位<el-input v-model="interviewReviewForm.position"/></label><label>面试轮次<el-input-number v-model="interviewReviewForm.round_no" :min="1" :max="3"/></label><label>面试官<el-input v-model="interviewReviewForm.interviewer"/></label><label>面试时间<DateTimePicker v-model="interviewReviewForm.interview_time"/></label><label>时长<el-select v-model="interviewReviewForm.duration" clearable placeholder="点击选择时长"><el-option v-if="interviewReviewForm.duration&&!durationOptions.includes(interviewReviewForm.duration)" :label="`原始值：${interviewReviewForm.duration}`" :value="interviewReviewForm.duration"/><el-option v-for="duration in durationOptions" :key="duration" :label="duration" :value="duration"/></el-select></label></div>
    <label>面试总结<el-input v-model="interviewReviewForm.summary" type="textarea" :rows="3"/></label>
    <label>讨论主题（每行一项）<el-input v-model="interviewReviewForm.topics" type="textarea" :rows="2"/></label><label>候选人具体表现与依据（每行一项）<el-input v-model="interviewReviewForm.performance" type="textarea" :rows="3"/></label><label>有依据的优势（每行一项）<el-input v-model="interviewReviewForm.strengths" type="textarea" :rows="2"/></label><label>待核实问题（每行一项）<el-input v-model="interviewReviewForm.concerns" type="textarea" :rows="2"/></label><label>后续跟进（每行一项）<el-input v-model="interviewReviewForm.follow_ups" type="textarea" :rows="2"/></label><label>给面试官的建议（每行一项）<el-input v-model="interviewReviewForm.suggestions" type="textarea" :rows="2"/></label>
    <div class="score-edit-header"><strong>能力评分（1–5 分）</strong><button class="link-action" @click="interviewReviewForm.scores.push({dimension:'',score:null,evidence:'',reasoning:''})">添加维度</button></div>
    <p class="management-note">可修改或留空；填写分数时请提供逐字稿依据。评分仅供参考，由面试官决定结果。</p>
    <div v-for="(score,i) in interviewReviewForm.scores" :key="i" class="score-edit"><div class="edit-grid"><label>能力维度<el-input v-model="score.dimension" placeholder="例如：问题解决"/></label><label>评分（留空表示证据不足）<el-input-number v-model="score.score" :min="1" :max="5" :step="0.5"/></label></div><label>逐字稿依据<el-input v-model="score.evidence" type="textarea" :rows="2"/></label><label>评分理由 / 待核实内容<el-input v-model="score.reasoning" type="textarea" :rows="2"/></label><button class="link-action" @click="interviewReviewForm.scores.splice(i,1)">删除维度</button></div>
    <label>面试官选择<el-radio-group v-model="interviewReviewForm.decision"><el-radio value="PENDING">待定</el-radio><el-radio value="REJECT">淘汰</el-radio><el-radio value="PASS">推进</el-radio></el-radio-group></label>
   </div><template #footer><button class="primary-button" :disabled="interviewReviewBusy" @click="confirmInterviewReview">{{interviewReviewBusy?'提交中…':'确认并执行'}}</button></template>
  </el-dialog>
  <el-drawer v-model="showDetail" size="min(560px, 95vw)" :title="detail?`${detail.application.candidate_name} · 招聘进度`:'招聘进度详情'">
   <div v-if="detail" class="drawer-content">
    <div class="detail-person"><span class="detail-avatar">{{detail.candidate.name.slice(0,1)}}</span><div><h2>{{detail.candidate.name}}</h2><p>{{detail.application.position}}</p></div></div>
    <div class="detail-stage"><span>当前招聘阶段</span><b>{{detail.application.stage_label}}</b></div>
    <div class="detail-section"><h3>候选人档案</h3><div class="detail-list"><span>电话</span><b>{{detail.candidate.phone||'未提供'}}</b><span>邮箱</span><b>{{detail.candidate.email||'未提供'}}</b><span>学历</span><b>{{detail.candidate.education||'未提供'}}</b><span>工作年限</span><b>{{detail.candidate.work_years==null?'未提供':detail.candidate.work_years+' 年'}}</b><span>主要技能</span><b>{{detail.candidate.skills||'未提供'}}</b></div></div>
    <div class="detail-section"><h3>简历 ({{detail.resumes.length}})</h3><p v-if="!detail.resumes.length" class="fine-empty">暂无简历，可在候选人管理中上传或填写。</p><div v-for="resume in detail.resumes" :key="resume.id" class="transcript-summary"><p><strong>{{resume.filename}}</strong> · {{fmt(resume.uploaded_at)}} · <a :href="`/api/v1/management/resumes/${resume.id}/download`">下载</a></p><details><summary>查看简历文字</summary><pre>{{resume.text}}</pre></details></div></div>
    <div class="detail-section"><h3>面试记录 ({{detail.interviews.length}})</h3><div v-if="!detail.interviews.length" class="fine-empty">暂无面试安排</div>
     <div v-for="iv in detail.interviews" :key="iv.id" class="interview-item"><div class="interview-round">{{iv.round_no}} 面</div><div class="interview-body"><b>{{iv.result==='PASS'?'通过':iv.result==='REJECT'?'未通过':'待定'}}</b><p>{{iv.scheduled_at||'暂无时间'}} · {{iv.interviewer||'未指定面试官'}}</p><blockquote v-if="iv.evaluation">{{iv.evaluation}}</blockquote>
      <label v-if="iv.status==='SCHEDULED'&&detail.application.stage===`ROUND${iv.round_no}_SCHEDULED`" class="file-picker transcript-picker"><Paperclip :size="15"/><span>{{transcriptBusy===iv.id?'正在生成总结...':iv.transcript?'重新上传面试文字':'上传完整面试文字'}}</span><input type="file" accept=".txt,.pdf,.docx" :disabled="!!transcriptBusy" @change="uploadTranscript($event,iv.id,detail.application.id)"/></label>
      <p v-if="modelSettings.mode==='demo'&&iv.status==='SCHEDULED'&&detail.application.stage===`ROUND${iv.round_no}_SCHEDULED`" class="transcript-hint">规则演示会提取基础信息和主题统计，摘要明确标注为非 AI。</p>
      <div v-if="iv.transcript" class="transcript-summary"><small>{{iv.transcript.filename}} · {{iv.transcript.characters}} 字 · {{fmt(iv.transcript.created_at)}} · {{iv.transcript.model}}</small>
       <p><strong>关联记录：</strong>{{detail.candidate.name}} · {{detail.application.position}} · {{iv.round_no}} 面</p>
       <p><strong>{{iv.transcript.review?'面试官核对':'文字中识别'}}：</strong>{{(iv.transcript.review?.evaluation||iv.transcript.summary).candidate_name||'姓名未提及'}} · {{(iv.transcript.review?.evaluation||iv.transcript.summary).position||'岗位未提及'}} · {{(iv.transcript.review?.evaluation||iv.transcript.summary).round_no?(iv.transcript.review?.evaluation||iv.transcript.summary).round_no+' 面':'轮次未提及'}} · {{(iv.transcript.review?.evaluation||iv.transcript.summary).interviewer||'面试官未提及'}} · {{(iv.transcript.review?.evaluation||iv.transcript.summary).interview_time||'时间未提及'}}<span v-if="(iv.transcript.review?.evaluation||iv.transcript.summary).duration"> · {{(iv.transcript.review?.evaluation||iv.transcript.summary).duration}}</span></p>
       <p><strong>面试总结：</strong>{{(iv.transcript.review?.evaluation||iv.transcript.summary).summary}}</p>
       <p v-if="(iv.transcript.review?.evaluation||iv.transcript.summary).topics?.length"><strong>讨论主题：</strong>{{(iv.transcript.review?.evaluation||iv.transcript.summary).topics.join('；')}}</p>
       <p v-if="(iv.transcript.review?.evaluation||iv.transcript.summary).performance?.length"><strong>候选人具体表现：</strong></p><ul v-if="(iv.transcript.review?.evaluation||iv.transcript.summary).performance?.length" class="interview-performance"><li v-for="(item,index) in (iv.transcript.review?.evaluation||iv.transcript.summary).performance" :key="index">{{item}}</li></ul>
       <div v-if="(iv.transcript.review?.evaluation||iv.transcript.summary).scores?.length" class="interview-scores"><strong>能力评分 · 1–5 分</strong><div v-for="(score,index) in (iv.transcript.review?.evaluation||iv.transcript.summary).scores" :key="index" class="interview-score"><div><b>{{score.dimension}}</b><span>{{score.score==null?'证据不足':`${score.score} / 5`}}</span></div><p v-if="score.evidence">依据：{{score.evidence}}</p><p v-if="score.reasoning">说明：{{score.reasoning}}</p></div><small>评分供面试官参考，不自动决定结果。</small></div>
       <p v-if="(iv.transcript.review?.evaluation||iv.transcript.summary).strengths?.length"><strong>有据可查的表现：</strong>{{(iv.transcript.review?.evaluation||iv.transcript.summary).strengths.join('；')}}</p>
       <p v-if="(iv.transcript.review?.evaluation||iv.transcript.summary).concerns?.length"><strong>待核实问题：</strong>{{(iv.transcript.review?.evaluation||iv.transcript.summary).concerns.join('；')}}</p>
       <p v-if="(iv.transcript.review?.evaluation||iv.transcript.summary).follow_ups?.length"><strong>后续跟进：</strong>{{(iv.transcript.review?.evaluation||iv.transcript.summary).follow_ups.join('；')}}</p>
       <p v-if="(iv.transcript.review?.evaluation||iv.transcript.summary).suggestions?.length"><strong>给面试官的建议：</strong>{{(iv.transcript.review?.evaluation||iv.transcript.summary).suggestions.join('；')}}</p>
       <p v-if="iv.transcript.review"><strong>评估关联结果：</strong>{{iv.transcript.review.decision==='PASS'?'推进':iv.transcript.review.decision==='REJECT'?'淘汰':'待定'}}<span v-if="iv.transcript.review.status==='DEFERRED'&&iv.result!=='PENDING'">；后续面试结果已更新为{{iv.result==='PASS'?'通过':'未通过'}}</span></p>
       <button v-if="iv.transcript.review?.status!=='FINAL'&&['ROUND'+iv.round_no+'_SCHEDULED','ROUND'+iv.round_no+'_FEEDBACK'].includes(detail.application.stage)" class="primary-button assessment-decision" @click="openInterviewReview(iv)">核对并选择处理结果</button>
       <details><summary>查看完整面试文字</summary><pre>{{iv.transcript.text}}</pre></details>
      </div>
     </div></div>
    </div>
    <div class="detail-section"><h3>招聘事件时间线</h3><el-timeline><el-timeline-item v-for="e in detail.events" :key="e.id" :timestamp="fmt(e.created_at)" placement="top"><b>{{e.new_stage}}</b><p class="timeline-text">{{e.type}} · {{e.operator}}</p><p v-if="e.data?.evaluation" class="timeline-text">{{e.data.evaluation}}</p></el-timeline-item></el-timeline></div>
   </div>
  </el-drawer>
 </div>
</template>
