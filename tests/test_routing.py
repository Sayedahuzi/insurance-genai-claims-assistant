from app.assistant import route_question

def test_claim_routes_to_sql():
    assert route_question('What is the status of claim CLM300210?') == 'claim_sql'
def test_claim_analysis_routes_to_combined_tools():
    assert route_question('Analyze claim CLM300500 and tell me if documents are missing.') == 'claim_analysis'
def test_policy_routes_to_rag():
    assert route_question('What is the maternity waiting period under Health Secure Plus?') == 'policy_rag'
def test_policy_id_routes_to_sql():
    assert route_question('Show policy POL200000') == 'policy_sql'
