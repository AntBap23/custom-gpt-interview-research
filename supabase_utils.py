import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def sign_up(email, password):
    return supabase.auth.sign_up({"email": email, "password": password})

def sign_in(email, password):
    return supabase.auth.sign_in_with_password({"email": email, "password": password})

def get_user():
    return supabase.auth.get_user()

def insert_interview(user_id, data):
    return supabase.table("interviews").insert({"user_id": user_id, **data}).execute()

def get_user_plan(user_id):
    res = supabase.table("users").select("plan_type").eq("id", user_id).single().execute()
    return res.data["plan_type"] if res.data else "free"

def set_user_plan(user_id, plan_type):
    return supabase.table("users").update({"plan_type": plan_type}).eq("id", user_id).execute()

def upload_file(user_id, file, filename):
    path = f"{user_id}/{filename}"
    supabase.storage.from_("files").upload(path, file)
    return path

def list_files(user_id):
    return supabase.storage.from_("files").list(user_id)
