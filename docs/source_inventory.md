# Source and output inventory

Based on the semantic model supplied October 8, 2026. `config/refresh.json` is the authoritative column allowlist. Only physical source columns are extracted; DAX calculated columns/measures stay in Power BI.

## Raw sources (34)

| Source / CSV filename stem | Required columns |
|---|---|
| account | account_code, account_key, active, begin_date, category_1099, description, end_date, entry_allowed, hide_income_stmt_hdr, project_required, type |
| assignment_view | assignment_key, assignment_type, begin_date, bill_customer_code, bill_customer_key, bill_rate, bill_rate_currency, bill_rate_source, budget_hours, cost_customer_code, cost_customer_key, cost_rate, cost_rate_currency, cost_rate_source, cost_struct_labor_key, edc, end_date, etc_hours, exceed_budget, labor_category, labor_category_key, last_etc_update_date, location, location_key, person_active, person_bill_rate, person_cost_rate, person_customer_code, person_customer_key, person_key, person_labor_category, person_labor_category_key, person_location, person_location_key, project_code, project_customer_code, project_customer_key, project_key, project_manager_key, project_status_key, project_type_key, task_key, use_wbs_dates |
| billing_type | billing_type_key, code, description |
| contract | award_date, begin_date, business_size_classification, ceiling_amount, classified_contract_flag, contract_billing_analyst_key, contract_code, contract_key, contract_manager_key, contract_officer, contract_purpose, contract_status_key, contract_title, currency_code_key, customer_key, dcaa_office, dpas_purchase_rating, end_customer_key, end_date, naics_code_key_primary, naics_code_key_supporting, other_clearance, owning_org_key, prime_contract_key, prime_or_sub, sbsa_flag, sbsa_recertification_date, sca_rate_flag, security_clearance, usc_restrictions_flag, user01, user02 |
| cost_element | account_number, code, cost_element_key, cost_element_type, description, sort_order |
| customer | account_number, active, begin_date, classification, created_timestamp, currency_code_key, customer_code, customer_key, customer_name, customer_size, customer_type_key, default_gl_post_org_key, default_person_org_flag, email_1099, end_date, entry_allowed, expense_policy_key, federal_tax_id, federal_tax_id_type, financial_org, industry, last_project_code_seq, last_updated_timestamp, legal_entity, legal_entity_key, recipient_name_1099, sector, sic_code, start_with_project_code_seq, stock_symbol, tax1, tax2, tax3, transact_elimination_flag, url, user01, user02, user03, user04, user05, user06, user07, user08, user09, user10, user11, user12, user13, user14, user15, user16, user17, user18, user19, user20, vendor_1099 |
| fiscal_month | begin_date, end_date, fiscal_month_key, fiscal_quarter_key, fiscal_year_key, period_number |
| fiscal_year | begin_date, end_date, fiscal_year_key, name, rate_update_date |
| fp_revenue_schedule | amount, fixed_price_key, fp_revenue_schedule_key, instance_amount, instance_exchange_rate, local_amount, local_exchange_rate, post_history_key, rev_date |
| general_ledger | account_key, credit_amount, customer_key, debit_amount, description, document_number, feature, fiscal_month_key, general_ledger_key, instance_credit_amount, instance_debit_amount, local_credit_amount, local_currency, local_debit_amount, organization_key, person_key, post_date, project_key, quantity, reference, transaction_currency, transaction_date |
| invoice | ach_max_amount, ach_min_amount, allowed_ach, allowed_credit_card, allowed_online_payment, amount, auto_correct_rounding, bill_to_city, bill_to_country, bill_to_first_name, bill_to_last_name, bill_to_middle_initial, bill_to_postal_code, bill_to_state_province, bill_to_street1, bill_to_street2, bill_to_street3, bill_to_suffix, billed_account_key, billed_organization_key, billing_from_date, billing_through, company_logo, completed_by, completed_date, contract_number, controller_key, created_by, created_date, credit_card_max_amount, credit_card_min_amount, currency, customer_key, description, discount_amount, discount_date, due_date, emailed_by, emailed_timestamp, enable_reminder, extracted_by, extracted_date, fee_pass_through, funded_value, historical_data_load_key, instance_amount, instance_exchange_rate, invoice_date, invoice_format_key, invoice_key, invoice_number, invoice_option, local_amount, local_currency, local_exchange_rate, memo, order_number, payment_term_key, post_date, printed_by, printed_timestamp, project_key, reminder_frequency, reminder_template_key, remit_to_city, remit_to_country, remit_to_first_name, remit_to_last_name, remit_to_middle_initial, remit_to_postal_code, remit_to_state_province, remit_to_street1, remit_to_street2, remit_to_street3, remit_to_suffix, ship_to_city, ship_to_country, ship_to_first_name, ship_to_last_name, ship_to_middle_initial, ship_to_postal_code, ship_to_state_province, ship_to_street1, ship_to_street2, ship_to_street3, ship_to_suffix, show_company_logo, show_contract_number, show_order_number, show_proj_code, show_proj_funded_value, show_proj_org_code, show_proj_title, signer_key, status, submitted_by, submitted_timestamp, voided_invoice_key, voiding_invoice_key |
| labor_category | account_number, active, description, labor_category, labor_category_key, occupation_key |
| pay_code | active, default_list, default_selected, description, exempt_usage, factor, pay_code, pay_code_key |
| person | activation_pending, active, allow_items, ar_approval_amount, assignment_email, business_week_key, created_timestamp, currency_code_key, currency_key, customer_invoice_email, customer_key, default_legal_entity_key, email, emp_id, employee_type_key, expense_approval_amount, expense_email, expense_vendor_key, first_name, hide_vat, hire_date, hour_increment, integration_user, integration_user_type, labor_category_key, last_modified_timestamp, last_name, leave_request_email, location_key, login_failures, middle_initial, pay_code_key, payment_currency_key, payment_method_key, person_code, person_key, po_form_title, po_signature_key, project_key, purchase_approval_amount, purchase_email, subcontractor, subk_user_account_activated, suffix, task_key, tbd_user, time_period_key, time_vendor_key, timesheet_email, timesheet_lines, tito_button_setting, tito_required, user01, user02, user03, user05, user06, user07, user08, user09, user10, user11, user12, user13, user14, user15, user16, user17, user18, user19, user20, username, vehicle_number, vendor_invoice_person |
| person_time | adjustment_date, adjustment_status, begin_date, comments, control_key, date_completed, dilution_bus_hours, dilution_bus_hours_factor, dilution_calc_req, dilution_factor, dilution_hours, historical, last_drawer_state, last_updated_timestamp, person_key, person_time_key, punch_clock_timesheet, status, time_period_key |
| person_time_data | additional_pay, adjusted_head, adjusted_number, adjustment_reason, batch_key, bill_amount, bill_currency, bill_customer, bill_local_exchange_rate, bill_rate, comments, cost_amount, cost_currency, cost_customer, cost_post_history_key, cost_rate, cost_struct_labor_key, eff_bill_rate, eff_cost_rate, eff_quantity, ic_cost_amount, ic_cost_currency, ic_cost_post_history_key, ic_cost_rate, ic_cost_struct_labor_key, ic_eff_cost_rate, ic_revenue_post_history_key, instance_bill_exchange_rate, instance_cost_exchange_rate, instance_ic_cost_exchange_rate, instance_local_exchange_rate, invoice_key, labor_category_key, last_update, local_bill_exchange_rate, local_cost_exchange_rate, local_ic_cost_exchange_rate, location_key, modified_person_key, pay_code_key, pending_adjustment, pending_head, person_time_key, pilob_post_history_key, po_key, po_labor_line_descriptor_key, post_date, post_history_key, proj_bill_exchange_rate, project_key, project_type_key, quantity, rejection_reason, source_bill_rate, source_bill_rate_currency, task_key, time_data_key, user01, user02, user03, user04, user05, vendor_invoice_key, work_date |
| planned_time | begin_date, bill_rate, bill_rate_currency, bill_rate_source, block_out, cost_rate, cost_rate_currency, cost_rate_source, cost_struct_labor_key, end_date, ic_cost_rate, ic_cost_struct_labor_key, labor_category_key, location_key, person_key, plan_set_key, planned_hours, planned_time_key, project_key, resource_request_key, task_key, use_wbs_dates |
| project | account_number, advanced_costing_flag, allow_self_plan, assignment_flag, bill_rate_source, billing_type_key, completed_date, contract_key, cost_rate_source, cost_struct_key, cost_struct_labor_key, created, created_timestamp, customer_approves_first, customer_key, enforce_wbs_dates, er_task_required, exp_bill_budget, exp_bill_est_tot, exp_bill_etc, exp_cost_budget, exp_cost_burden_budget, exp_cost_est_tot, exp_cost_etc, exp_sub_po_required, expense_assignment_flag, funded_cost, funded_fee, funded_value, future_charge, hours_budget, hours_est_tot, hours_etc, ic_apply_billing_markup, ic_cost_struct_labor_key, ic_cost_struct_odc_key, ic_effort_flag, item_assignment_flag, item_task_required, labor_bill_budget, labor_bill_est_tot, labor_bill_etc, labor_cost_budget, labor_cost_burden_budget, labor_cost_est_tot, labor_cost_etc, last_updated_timestamp, leave_balance, limit_bill_to_funded, limit_rev_to_funded, location_key, location_required, orig_end_date, orig_funded_cost, orig_funded_fee, orig_funded_value, orig_start_date, orig_total_cost, orig_total_fee, orig_total_value, owning_customer_key, pay_code_key, pct_complete_rule, percent_complete, pm_approves_before_mgr, posting_group_key, probability_percent, proj_require_time_comments, project_billing_currency, project_code, project_color, project_currency, project_key, project_status_key, project_type_key, purpose, rev_end_date, rev_start_date, self_assign_plans, task_level_assignment, time_assignment_flag, title, tito_required, total_cost, total_fee, total_value, ts_sub_po_required, ts_task_required, use_labor_category, user01, user02, user03, user04, user05, user06, user07, user08, user09, user10, user11, user12, user13, user14, user15, user16, user17, user18, user19, user20 |
| project_budget_history | completed_date, enforce_wbs_dates, exp_bill_budget, exp_bill_est_tot, exp_bill_etc, exp_cost_budget, exp_cost_burden_budget, exp_cost_est_tot, exp_cost_etc, funded_cost, funded_fee, funded_value, hours_budget, hours_est_tot, hours_etc, labor_bill_budget, labor_bill_est_tot, labor_bill_etc, labor_cost_budget, labor_cost_burden_budget, labor_cost_est_tot, labor_cost_etc, modified_by, modified_date, orig_end_date, orig_funded_cost, orig_funded_fee, orig_funded_value, orig_start_date, orig_total_cost, orig_total_fee, orig_total_value, pct_complete_rule, percent_complete, probability_percent, project_budget_history_key, project_key, rev_end_date, rev_start_date, total_cost, total_fee, total_value |
| project_status | open_status, project_status_key, status |
| cost_struct_labor | cost_element_key, cost_struct_key, cost_struct_labor_key |
| expense_data_allocation | amount, billable, cost_struct_odc_key, expense_data_key, project_key, task_key |
| expense_data | expense_data_key, expense_date |
| cost_struct_odc | cost_element_key, cost_struct_odc_key |
| fin_document_detail | account_key, credit_amount, debit_amount, fin_document_detail_key, fin_document_key, transaction_date |
| fin_document_detail_expense | amount, bill_amount, cost_struct_odc_key, fin_document_detail_key |
| fin_document_detail_labor | amount, cost_struct_labor_key, fin_document_detail_key |
| fin_document_det_proj_expense | expense_type_key, fin_document_detail_key, project_key, project_type_key, task_key |
| fin_document_det_proj_labor | cost_rate, fin_document_detail_key, hours, labor_category_key, project_key, project_type_key, task_key |
| cost_struct_pool | cost_element_key, cost_struct_key, cost_struct_pool_key, description, display_sequence, formula, process_sequence |
| cost_struct_pool_rate | actual_rate, cost_struct_pool_key, fiscal_year_key, provisional_rate, target_rate |
| cost_report_element | actuals_formula, budget_formula, cost_report_element, cost_report_element_key, cost_report_key, sequence, total_ind, use_in_rev_report, value_format |
| cost_report | cost_report, cost_report_key, description |
| fiscal_month_org_feature_close | closed_by, closed_timestamp, customer_key, feature, fiscal_month_key |

## Reporting outputs (26)

| Existing model table | Preparation |
|---|---|
| Cost Pool Rules | Cost Pool Rules |
| Cost Report Rules | Cost Report Rules |
| Financial Document Cost Detail | Financial Document Cost Detail |
| Fiscal Period Close | Fiscal Period Close |
| Project Cost Details | Project Cost Details |
| account_Table | Selected columns from account; model renames preserved |
| assignment_view_Table | Selected columns from assignment_view; model renames preserved |
| billing_type | Selected columns from billing_type; model renames preserved |
| contract_Table | Selected columns from contract; model renames preserved |
| cost_element | Selected columns from cost_element; model renames preserved |
| customer_Table | Selected columns from customer; model renames preserved |
| fiscal_month_Table | Selected columns from fiscal_month; model renames preserved |
| fiscal_year_Table | Selected columns from fiscal_year; model renames preserved |
| fp_revenue_schedule | Selected columns from fp_revenue_schedule; model renames preserved |
| general_ledger_Table | Selected columns from general_ledger; model renames preserved |
| invoice | Selected columns from invoice; model renames preserved |
| labor_category_Table | Selected columns from labor_category; model renames preserved |
| pay_code | Selected columns from pay_code; model renames preserved |
| person_Table | Selected columns from person; model renames preserved |
| person_time | Selected columns from person_time; model renames preserved |
| person_time_data_Table | Selected columns from person_time_data; model renames preserved |
| planned_time_Table | Selected columns from planned_time; model renames preserved |
| planned_time_daily_Table | planned_time_daily_Table |
| project_Table | Selected columns from project; model renames preserved |
| project_budget_history_Table | Selected columns from project_budget_history; model renames preserved |
| project_status_Table | Selected columns from project_status; model renames preserved |

Project Cost Details combines labor (`quantity × eff_cost_rate`), expense allocations (`amount`), financial expense (`amount`) and financial labor (`amount`). Effective quantity is retained but is not substituted for quantity. Financial labor is not recomputed from hours/rate. Financial Document Cost Detail contains just the two financial branches. All joins are left joins, preserving duplicate/null-key matches as the model does.

Cost Pool Rules joins classifications and rates. Cost Report Rules joins report metadata. Fiscal Period Close joins fiscal-month metadata and casts dates. Planned daily time expands inclusive Monday–Friday dates and distributes planned hours evenly, without holidays; missing/reversed/weekend-only ranges produce no daily rows. Direct account/project outputs preserve Account Title/Type renames. Contract, person and assignment fields removed by the model are not extracted unless separately required by an output.

## Outside the pipeline

- CPARs: Existing SharePoint source.
- Date Table: DAX calculated or local table stays in Power BI.
- Finance Waterfall Steps: DAX calculated or local table stays in Power BI.
- Funding Pace Metrics: DAX calculated or local table stays in Power BI.
- HR Retention and Turnover: Existing SharePoint source.
- Master Crosswalk: Existing SharePoint source.
- Monthly Pulse: Existing SharePoint source.
- Project Reporting Rules: DAX calculated or local table stays in Power BI.
- Unanet Name Mapping: Existing SharePoint source.
- VOC Tracking: Existing SharePoint source.
- _Measures: DAX calculated or local table stays in Power BI.

Unused intermediate queries such as task, expense_type, fin_document, funding_cap_adjustment and diagnostic queries are not staged. Remove obsolete ODBC dependencies during Power BI cutover after checking references. Do not delete loaded model tables solely because they are intermediates in the extraction.
