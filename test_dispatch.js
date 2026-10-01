const { createClient } = require('@supabase/supabase-js');
const supabaseUrl = 'https://cryfgdedvnyczhausidk.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNyeWZnZGVkdm55Y3poYXVzaWRrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4OTQwMDU3MSwiZXhwIjoyMTA0OTc2NTcxfQ.3RRFtT--ublCzZZhfSyM0HodY0Goxtb-HrddJkCBLAU';
const supabaseClient = createClient(supabaseUrl, supabaseKey);
const jsonObj = {
    "timestamp": new Date().toISOString(),
    "system": "TARANG_SURVEY_OPS",
    "destination": "MARINE_ANALYST",
    "exported_tier": ["A", "B"],
    "total_detections": 1,
    "detections": [{ id: "test1", classification_tier: "A" }]
};
async function run() {
    const { data, error } = await supabaseClient.from('dispatches').insert([ { payload: jsonObj } ]);
    console.log("INSERT: ", data, error);
    
    const res = await supabaseClient.from('dispatches').select('*').limit(1).order('created_at', { ascending: false });
    console.log("LATEST: ", res.data);
}
run();
