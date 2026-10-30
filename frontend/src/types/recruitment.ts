export type AppRow = {
 id:string; candidate_id:string; candidate_name:string; position:string; stage:string;
 stage_label:string; round_no:number; owner:string; version:number; updated_at:string
}

export type InterviewScore = {dimension:string;score:number|null;evidence:string;reasoning:string}
export type ModelSettings = {mode:'demo'|'server'|'custom';model:string;base_url:string;api_key:string}
export type InterviewSummary = {
 candidate_name:string|null;position:string|null;round_no:number|null;interviewer:string|null;
 interview_time:string|null;duration:string|null;summary:string;topics:string[];
 performance?:string[];scores?:InterviewScore[];strengths:string[];concerns:string[];
 follow_ups:string[];suggestions:string[]
}
