import axios from 'axios'

export function errorMessage(error:unknown):string {
 if (axios.isAxiosError(error)) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
   const messages=detail.map(item=>typeof item?.msg==='string'?item.msg:'').filter(Boolean)
   if (messages.length) return messages.join('；')
  }
  return error.message || '请求失败'
 }
 return error instanceof Error ? error.message : '操作失败'
}
