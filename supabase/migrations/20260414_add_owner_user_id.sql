alter table public.studies add column if not exists owner_user_id uuid references auth.users(id) on delete cascade;
alter table public.protocols add column if not exists owner_user_id uuid references auth.users(id) on delete cascade;
alter table public.personas add column if not exists owner_user_id uuid references auth.users(id) on delete cascade;
alter table public.question_guides add column if not exists owner_user_id uuid references auth.users(id) on delete cascade;
alter table public.transcripts add column if not exists owner_user_id uuid references auth.users(id) on delete cascade;
alter table public.simulations add column if not exists owner_user_id uuid references auth.users(id) on delete cascade;
alter table public.gioia_analyses add column if not exists owner_user_id uuid references auth.users(id) on delete cascade;
alter table public.comparisons add column if not exists owner_user_id uuid references auth.users(id) on delete cascade;

create index if not exists idx_studies_owner_user_id on public.studies(owner_user_id);
create index if not exists idx_protocols_owner_user_id on public.protocols(owner_user_id);
create index if not exists idx_personas_owner_user_id on public.personas(owner_user_id);
create index if not exists idx_question_guides_owner_user_id on public.question_guides(owner_user_id);
create index if not exists idx_transcripts_owner_user_id on public.transcripts(owner_user_id);
create index if not exists idx_simulations_owner_user_id on public.simulations(owner_user_id);
create index if not exists idx_gioia_analyses_owner_user_id on public.gioia_analyses(owner_user_id);
create index if not exists idx_comparisons_owner_user_id on public.comparisons(owner_user_id);
