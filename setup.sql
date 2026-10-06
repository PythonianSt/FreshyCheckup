begin;
create table if not exists public.student_physical_exam_records (
 record_id uuid primary key,
 student_id text not null,faculty text not null,created_at_bkk timestamptz not null default now(),
 examiner text not null,color_vision jsonb not null,stroop jsonb not null,examinations jsonb not null,
 general_note text not null default '',schema_version integer not null default 1
);
alter table public.student_physical_exam_records enable row level security;
revoke all on public.student_physical_exam_records from anon,authenticated;
revoke update,delete,truncate on public.student_physical_exam_records from service_role;
grant select,insert on public.student_physical_exam_records to service_role;
create index if not exists student_physical_exam_sid_date_idx on public.student_physical_exam_records(student_id,created_at_bkk desc);
-- Deliberately preserve opd_records and the live Alert trigger/table.
notify pgrst,'reload schema';
commit;
