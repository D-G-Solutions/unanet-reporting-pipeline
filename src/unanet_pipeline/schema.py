"""Source selections and output schema from the consolidated Power Query."""
TABLES = {
 'person_time_data': ['project_key','task_key','work_date','eff_quantity','eff_cost_rate','quantity','cost_struct_labor_key'],
 'cost_struct_labor': ['cost_struct_labor_key','cost_struct_key','cost_element_key'],
 'expense_data_allocation': ['expense_data_key','cost_struct_odc_key','project_key','task_key','amount','billable'],
 'expense_data': ['expense_data_key','expense_date'],
 'cost_struct_odc': ['cost_struct_odc_key','cost_element_key'],
 'cost_element': ['cost_element_key','code'],
 'fin_document_detail': ['fin_document_detail_key','fin_document_key','account_key','transaction_date','debit_amount','credit_amount'],
 'fin_document_detail_expense': ['fin_document_detail_key','amount','bill_amount','cost_struct_odc_key'],
 'fin_document_detail_labor': ['fin_document_detail_key','amount','cost_struct_labor_key'],
 'fin_document_det_proj_expense': ['fin_document_detail_key','project_key','task_key','expense_type_key','project_type_key'],
 'fin_document_det_proj_labor': ['fin_document_detail_key','project_key','task_key','project_type_key','labor_category_key','hours','cost_rate'],
}
OUTPUT = ['project_key','task_key','eff_quantity','eff_cost_rate','cost_struct_key','cost_element_key','Cost Amount','Cost Source','billable','code','fin_document_detail_key','expense_type_key','project_type_key','fin_document_key','account_key','debit_amount','credit_amount','bill_amount','cost_struct_odc_key','labor_category_key','hours','cost_rate','cost_struct_labor_key','Cost Date','quantity']
NUMBERS = {'eff_quantity','eff_cost_rate','quantity','amount','debit_amount','credit_amount','bill_amount','hours','cost_rate','Cost Amount'}
DATES = {'work_date','expense_date','transaction_date','Cost Date'}
