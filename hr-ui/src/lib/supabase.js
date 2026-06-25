import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL  = "https://hdlrtjlqilqofrmwnwps.supabase.co";
const SUPABASE_ANON = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhkbHJ0amxxaWxxb2ZybXdud3BzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEyMzkwNjUsImV4cCI6MjA5NjgxNTA2NX0.-nshGvyjPzlJP3d3XSWHvUAPJLwRl_2uLXZa8nzTWZ4";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON);
