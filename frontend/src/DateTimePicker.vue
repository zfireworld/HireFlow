<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{modelValue:string|null|undefined; placeholder?:string}>()
const emit = defineEmits<{ 'update:modelValue':[value:string] }>()

// Keep unrecognized historical or model-generated values until the user replaces them.
const normalized = computed(() => {
 const value = props.modelValue?.trim()
 if (!value) return ''
 const match = value.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T](\d{1,2}):(\d{2})(?::\d{2})?$/)
 if (!match) return ''
 const [,year,month,day,hour,minute] = match
 const date = new Date(Number(year), Number(month)-1, Number(day), Number(hour), Number(minute))
 if (date.getFullYear()!==Number(year) || date.getMonth()!==Number(month)-1 || date.getDate()!==Number(day) || date.getHours()!==Number(hour) || date.getMinutes()!==Number(minute)) return ''
 return `${year}-${month.padStart(2,'0')}-${day.padStart(2,'0')} ${hour.padStart(2,'0')}:${minute}`
})
const unrecognized = computed(() => !!props.modelValue?.trim() && !normalized.value)
</script>

<template>
 <div class="date-time-field">
  <el-date-picker :model-value="normalized || null" type="datetime" format="YYYY-MM-DD HH:mm" value-format="YYYY-MM-DD HH:mm" :editable="false" :placeholder="placeholder || '点击选择日期和时间'" @update:model-value="emit('update:modelValue', $event || '')"/>
  <div v-if="unrecognized" class="date-time-original">原始时间无法自动识别：{{modelValue}}。请选择准确时间，或 <button type="button" @click="emit('update:modelValue','')">清除原值</button>。</div>
 </div>
</template>

<style scoped>
.date-time-field{width:100%;min-width:0}.date-time-field :deep(.el-date-editor){width:100%}.date-time-original{margin-top:6px;color:#ae7728;font-size:11px;line-height:1.5;overflow-wrap:anywhere}.date-time-original button{border:0;padding:0;background:none;color:#4779ce;cursor:pointer}
</style>
