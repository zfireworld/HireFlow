<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import type {AppRow} from './types/recruitment'
import {errorMessage as err} from './utils/errors'
import { ArrowRight, BriefcaseBusiness, CalendarDays, CheckCircle2, CircleHelp, FileText, GraduationCap, Lightbulb, Sparkles, UploadCloud } from 'lucide-vue-next'

type Evaluation = {candidate_name:string|null;position:string|null;education:string|null;skills:string|null;work_years:number|null;summary:string;strengths:string[];concerns:string[];suggestions:string[]}
type Assessment = {id:string;filename:string;application_id:string|null;evaluation:Evaluation;reviewed:Evaluation|null;model:string;status:string;decision:string|null;created_at:string}
const props=defineProps<{rows:AppRow[]}>()
const emit=defineEmits<{refresh:[];upload:[]}>()
const records=ref<Assessment[]>([])
const filter=ref<'ALL'|'PENDING'|'DEFERRED'|'FINAL'>('ALL')
const filters=computed(()=>[
 {id:'ALL' as const,label:'全部',count:records.value.length},
 {id:'PENDING' as const,label:'待确认',count:records.value.filter(r=>r.status==='PENDING').length},
 {id:'DEFERRED' as const,label:'待定',count:records.value.filter(r=>r.status==='DEFERRED').length},
 {id:'FINAL' as const,label:'已确认',count:records.value.filter(r=>r.status==='FINAL').length},
])
const visibleRecords=computed(()=>filter.value==='ALL'?records.value:records.value.filter(r=>r.status===filter.value))
const editing=ref<Assessment|null>(null)
const busy=ref(false)
const form=ref({application_id:'',candidate_name:'',position:'',education:'',skills:'',work_years:null as number|null,summary:'',strengths:'',concerns:'',suggestions:'',decision:''})
const lines=(value:string)=>value.split('\n').map(s=>s.trim()).filter(Boolean)
const statusText=(r:Assessment)=>r.status==='FINAL'?'已确认':r.status==='DEFERRED'?'待定':'待确认'
const decisionText=(r:Assessment)=>r.decision==='INTERVIEW'?'进入一面':r.decision==='REJECT'?'淘汰':'待定'

async function load(){
 try{records.value=(await axios.get('/api/v1/resume-assessments')).data}
 catch(e){ElMessage.error(err(e))}
}
function edit(record:Assessment){
 const x=record.reviewed||record.evaluation
 form.value={application_id:record.application_id||'',candidate_name:x.candidate_name||'',position:x.position||'',education:x.education||'',skills:x.skills||'',work_years:x.work_years,summary:x.summary||'',strengths:(x.strengths||[]).join('\n'),concerns:(x.concerns||[]).join('\n'),suggestions:(x.suggestions||[]).join('\n'),decision:''}
 editing.value=record
}
async function save(){
 const f=form.value
 if(!f.decision||!f.candidate_name.trim()||!f.position.trim()||!f.summary.trim()){ElMessage.warning('请核对姓名、岗位、评价，并选择处理结果');return}
 if(busy.value||!editing.value)return
 busy.value=true
 try{
  await axios.post(`/api/v1/resume-assessments/${editing.value.id}/decision`,{
   decision:f.decision,application_id:f.application_id||null,
   evaluation:{candidate_name:f.candidate_name.trim(),position:f.position.trim(),education:f.education||null,skills:f.skills||null,work_years:f.work_years,summary:f.summary.trim(),strengths:lines(f.strengths),concerns:lines(f.concerns),suggestions:lines(f.suggestions)}})
  ElMessage.success('已保存面试官确认结果');editing.value=null;emit('refresh');await load()
 }catch(e){ElMessage.error(err(e))}finally{busy.value=false}
}
onMounted(load)
</script>

<template>
 <div class="page-intro intro-inline resume-intro"><div><span class="eyebrow"><span class="eyebrow-dot"></span> RESUME ASSESSMENT</span><h1>简历评估</h1><p>浏览候选人信息和评估要点，核对后选择下一步。</p></div><button class="primary-button" @click="emit('upload')"><UploadCloud :size="17"/> 上传简历</button></div>
 <div class="resume-filter" role="group" aria-label="按评估状态筛选">
  <button v-for="f in filters" :key="f.id" :class="['resume-filter-item',{active:filter===f.id}]" :aria-pressed="filter===f.id" @click="filter=f.id">{{f.label}} <span>{{f.count}}</span></button>
 </div>
 <div v-if="!visibleRecords.length" class="panel blank-state resume-empty"><FileText :size="38"/><h3>{{records.length?'此状态暂无评估':'暂无简历评估'}}</h3><p>{{records.length?'切换筛选条件查看其他记录。':'上传简历后，这里会展示候选人信息和参考意见。'}}</p><button v-if="!records.length" class="text-button" @click="emit('upload')">上传第一份简历 <ArrowRight :size="15"/></button></div>
 <div v-for="r in visibleRecords" :key="r.id" class="panel resume-card">
  <div class="resume-card-top">
   <div class="resume-person"><div class="resume-avatar">{{(r.reviewed||r.evaluation).candidate_name?.slice(0,1)||'?'}}</div><div class="resume-identity"><div class="resume-name-row"><h2>{{(r.reviewed||r.evaluation).candidate_name||'候选人待确认'}}</h2><span :class="['resume-status',r.status==='FINAL'?'done':r.status==='DEFERRED'?'deferred':'pending']"><span></span>{{statusText(r)}}</span></div><p><BriefcaseBusiness :size="14"/> {{(r.reviewed||r.evaluation).position||'应聘岗位待确认'}}</p></div></div>
   <div class="resume-meta"><span><FileText :size="14"/> {{r.filename}}</span><span><CalendarDays :size="14"/> {{r.created_at.replace('T',' ').slice(0,16)}}</span></div>
  </div>
  <div class="resume-card-body">
   <div class="resume-facts"><div><span>学历</span><strong><GraduationCap :size="15"/> {{(r.reviewed||r.evaluation).education||'未提供'}}</strong></div><div><span>工作年限</span><strong>{{(r.reviewed||r.evaluation).work_years==null?'未提供':(r.reviewed||r.evaluation).work_years+' 年'}}</strong></div><div class="resume-skills"><span>主要技能</span><strong>{{(r.reviewed||r.evaluation).skills||'未提供'}}</strong></div></div>
   <section class="resume-overview"><div class="resume-section-heading"><div class="resume-section-icon indigo"><Sparkles :size="16"/></div><div><h3>评估概览</h3><small>{{r.model==='demo'?'规则演示 · 非 AI':r.reviewed?'面试官已修订 · '+r.model:'模型参考 · '+r.model}}</small></div></div><p>{{(r.reviewed||r.evaluation).summary}}</p></section>
   <div class="resume-insights"><section><div class="resume-section-heading"><div class="resume-section-icon teal"><CheckCircle2 :size="16"/></div><h3>相关优势</h3></div><ul v-if="(r.reviewed||r.evaluation).strengths?.length"><li v-for="(item,i) in (r.reviewed||r.evaluation).strengths" :key="i">{{item}}</li></ul><p v-else class="resume-empty-text">暂无已提取的优势</p></section><section><div class="resume-section-heading"><div class="resume-section-icon amber"><CircleHelp :size="16"/></div><h3>待核实事项</h3></div><ul v-if="(r.reviewed||r.evaluation).concerns?.length"><li v-for="(item,i) in (r.reviewed||r.evaluation).concerns" :key="i">{{item}}</li></ul><p v-else class="resume-empty-text">暂无待核实事项</p></section></div>
   <section v-if="(r.reviewed||r.evaluation).suggestions?.length" class="resume-suggestions"><div class="resume-section-heading"><div class="resume-section-icon blue"><Lightbulb :size="16"/></div><h3>面试建议</h3></div><ul><li v-for="(item,i) in (r.reviewed||r.evaluation).suggestions" :key="i">{{item}}</li></ul></section>
  </div>
  <div class="resume-card-bottom"><p>{{r.status==='FINAL'?'面试官已确认':'请核对信息后选择处理结果'}}</p><button v-if="r.status!=='FINAL'" class="primary-button" @click="edit(r)">核对并选择 <ArrowRight :size="15"/></button><span v-else class="resume-decision"><CheckCircle2 :size="15"/> {{decisionText(r)}}</span></div>
 </div>
 <el-dialog :model-value="!!editing" title="核对简历评估" width="min(650px, 95vw)" @close="editing=null">
  <div class="management-form resume-review-form">
   <p class="management-note">参考内容可修改。选择结果并确认后，系统才会创建或更新申请。</p>
   <label>关联已有申请（新建时留空）<el-select v-model="form.application_id" clearable filterable :disabled="editing?.status==='DEFERRED'" placeholder="新建申请请留空"><el-option v-for="a in props.rows" :key="a.id" :label="`${a.candidate_name} · ${a.position} · ${a.stage_label}`" :value="a.id"/></el-select></label>
   <div class="edit-grid"><label>候选人姓名<el-input v-model="form.candidate_name"/></label><label>应聘岗位<el-input v-model="form.position"/></label><label>学历<el-input v-model="form.education"/></label><label>工作年限<el-input-number v-model="form.work_years" :min="0" :max="80"/></label></div>
   <label>技能<el-input v-model="form.skills" type="textarea" :rows="2"/></label><label>简历评价<el-input v-model="form.summary" type="textarea" :rows="3"/></label>
   <label>相关优势（每行一项）<el-input v-model="form.strengths" type="textarea" :rows="2"/></label><label>待核实事项（每行一项）<el-input v-model="form.concerns" type="textarea" :rows="2"/></label><label>面试建议（每行一项）<el-input v-model="form.suggestions" type="textarea" :rows="2"/></label>
   <label>面试官选择<el-radio-group v-model="form.decision"><el-radio value="PENDING">待定</el-radio><el-radio value="REJECT">淘汰</el-radio><el-radio value="INTERVIEW">进入一面</el-radio></el-radio-group></label>
  </div><template #footer><button class="primary-button" :disabled="busy" @click="save">{{busy?'提交中…':'确认并执行'}}</button></template>
 </el-dialog>
</template>

<style scoped>
.resume-intro{margin-bottom:22px}
.resume-filter{display:flex;align-items:center;gap:6px;overflow-x:auto;margin:0 0 18px;padding:5px;background:#edf1f7;border-radius:11px;width:max-content;max-width:100%}
.resume-filter-item{display:flex;align-items:center;gap:8px;border:0;border-radius:8px;background:transparent;color:#78869a;font-size:12px;font-weight:600;padding:9px 12px;white-space:nowrap}
.resume-filter-item span{font-size:10px;color:#8998ad}.resume-filter-item.active{background:#fff;color:#365fb9;box-shadow:0 2px 8px #1b32520c}.resume-filter-item.active span{color:#5e7dc3}
.resume-empty{margin-top:6px}.resume-card{overflow:hidden;margin-bottom:18px}
.resume-card-top{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;padding:23px 26px;border-bottom:1px solid #edf1f6}
.resume-person{display:flex;align-items:center;gap:14px;min-width:0}.resume-avatar{display:grid;place-items:center;flex-shrink:0;width:48px;height:48px;border-radius:14px;background:#eaf0ff;color:#4b6fc0;font-size:19px;font-weight:700}
.resume-identity{min-width:0}.resume-name-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.resume-name-row h2{font-size:17px;line-height:1.4;color:#243650;overflow-wrap:anywhere}.resume-identity p{display:flex;align-items:center;gap:6px;margin-top:6px;color:#7f8fa6;font-size:12px;overflow-wrap:anywhere}
.resume-status{display:inline-flex;align-items:center;gap:6px;padding:5px 9px;border-radius:20px;font-size:10px;font-weight:600;white-space:nowrap}.resume-status span{width:6px;height:6px;border-radius:50%;background:currentColor}.resume-status.pending{background:#fff4e4;color:#b67b35}.resume-status.deferred{background:#f0f3f8;color:#77879c}.resume-status.done{background:#e8f7f0;color:#328d70}
.resume-meta{display:flex;align-items:flex-end;flex-direction:column;gap:8px;min-width:0;color:#99a6b7;font-size:11px}.resume-meta span{display:flex;align-items:center;gap:6px;max-width:240px;overflow-wrap:anywhere}.resume-meta svg{flex-shrink:0}
.resume-card-body{padding:21px 26px}.resume-facts{display:grid;grid-template-columns:minmax(100px,1fr) minmax(100px,1fr) minmax(180px,2fr);gap:18px;padding:15px 17px;border:1px solid #edf1f7;border-radius:10px;background:#fafbfd}.resume-facts>div{min-width:0}.resume-facts span{display:block;color:#99a6b7;font-size:10px;margin-bottom:7px}.resume-facts strong{display:flex;align-items:flex-start;gap:6px;color:#43546d;font-size:12px;font-weight:600;line-height:1.55;overflow-wrap:anywhere}.resume-facts svg{flex-shrink:0;margin-top:1px;color:#7992c5}
.resume-overview{margin-top:22px}.resume-section-heading{display:flex;align-items:center;gap:9px}.resume-section-heading h3{font-size:12px;color:#344761}.resume-section-heading small{display:block;font-size:10px;color:#9ba8ba;margin-top:3px}.resume-section-icon{width:30px;height:30px;display:grid;place-items:center;flex-shrink:0;border-radius:9px}.resume-section-icon.indigo{background:#edf1ff;color:#6178cc}.resume-section-icon.teal{background:#eaf8f2;color:#459c80}.resume-section-icon.amber{background:#fff5e8;color:#c3924d}.resume-section-icon.blue{background:#eaf3ff;color:#5b85c3}
.resume-overview>p{margin:11px 0 0 39px;font-size:12px;line-height:1.9;color:#596a82;white-space:pre-wrap;overflow-wrap:anywhere}.resume-insights{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:19px}.resume-insights section,.resume-suggestions{padding:15px 16px;border:1px solid #edf1f6;border-radius:10px;background:#fff}.resume-insights ul,.resume-suggestions ul{margin:10px 0 0;padding-left:20px;color:#596a82;font-size:11px;line-height:1.9;overflow-wrap:anywhere}.resume-insights li+li,.resume-suggestions li+li{margin-top:4px}.resume-empty-text{font-size:11px;color:#a3afbf;margin:11px 0 0 39px}.resume-suggestions{margin-top:14px;background:#f8faff;border-color:#edf2fb}
.resume-card-bottom{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:15px 26px;background:#fbfcfe;border-top:1px solid #edf1f6}.resume-card-bottom p{font-size:11px;color:#99a6b7}.resume-decision{display:flex;align-items:center;gap:6px;color:#478d74;font-size:12px;font-weight:600}.resume-review-form{max-height:min(65vh,680px);overflow-y:auto;padding:0 8px 4px 0}
@media(max-width:720px){.resume-card-top{flex-direction:column;gap:12px;padding:19px}.resume-meta{align-items:flex-start}.resume-card-body{padding:18px}.resume-facts{grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.resume-skills{grid-column:1 / -1}.resume-insights{grid-template-columns:1fr}.resume-card-bottom{padding:14px 18px}.resume-card-bottom p{max-width:160px;line-height:1.5}}
</style>
