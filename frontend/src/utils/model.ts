import type {ModelSettings} from '../types/recruitment'

export function modelConfig(settings:ModelSettings) {
 return settings.mode==='custom'
  ? {mode:settings.mode,model:settings.model.trim(),base_url:settings.base_url.trim(),api_key:settings.api_key}
  : {mode:settings.mode}
}

export function modelConfigComplete(settings:ModelSettings):boolean {
 return settings.mode!=='custom'||!!(settings.model.trim()&&settings.base_url.trim())
}
