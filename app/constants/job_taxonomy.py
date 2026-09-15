"""Fixed filter taxonomy transcribed from the client's feedback doc
("feedback website (v2)"). Single source of truth for the enum values
stored on `Job` rows; the frontend keeps a mirrored copy in
`constants/jobTaxonomy.ts` with the same slugs so labels never drift.

Each entry is (slug, Vietnamese label, English label). Slugs are what
get stored/validated/filtered on; labels are for display only.
"""

CATEGORY_L1 = [
    ("business_sales", "Kinh doanh/Bán hàng", "Business/Sales"),
    ("marketing_pr_ads", "Marketing/PR/Quảng cáo", "Marketing/PR/Advertising"),
    ("customer_service_ops", "Chăm sóc khách hàng/Vận hành", "Customer Service/Operations"),
    ("hr_admin_legal", "Nhân sự/Hành chính/Pháp chế", "HR/Admin/Legal"),
    ("it", "Công nghệ thông tin", "Information Technology"),
    ("finance_banking_insurance", "Tài chính/Ngân hàng/Bảo hiểm", "Finance/Banking/Insurance"),
    ("real_estate", "Bất động sản", "Real Estate"),
    ("construction", "Xây dựng", "Construction"),
    ("accounting_audit_tax", "Kế toán/Kiểm toán/Thuế", "Accounting/Audit/Tax"),
    ("manufacturing", "Sản xuất", "Manufacturing"),
    ("education_training", "Giáo dục/Đào tạo", "Education/Training"),
    ("retail_life_services", "Bán lẻ/Dịch vụ đời sống", "Retail/Life Services"),
    ("film_tv_media_publishing", "Phim/Truyền hình/Báo chí/Xuất bản", "Film/TV/Journalism/Publishing"),
    ("electrical_electronics_telecom", "Điện/Điện tử/Viễn thông", "Electrical/Electronics/Telecom"),
    ("logistics_procurement_warehouse", "Logistics/Thu mua/Kho/Vận tải", "Logistics/Procurement/Warehouse/Transport"),
    ("professional_consulting", "Tư vấn chuyên môn", "Professional Consulting"),
    ("pharma_healthcare_biotech", "Dược/Y tế/Sức khỏe/Công nghệ sinh học", "Pharma/Healthcare/Biotech"),
    ("design", "Thiết kế", "Design"),
    ("hospitality_tourism", "Nhà hàng/Khách sạn/Du lịch", "Restaurant/Hotel/Tourism"),
    ("energy_environment_agriculture", "Năng lượng/Môi trường/Nông nghiệp", "Energy/Environment/Agriculture"),
    ("general_labor", "Lao động phổ thông", "General Labor"),
    ("driver", "Tài xế", "Driver"),
    ("translation_interpretation", "Biên phiên dịch", "Translation/Interpretation"),
    ("law", "Luật", "Law"),
    ("other", "Nhóm nghề khác", "Other"),
]

EXPERIENCE_LEVEL = [
    ("no_experience", "Không yêu cầu kinh nghiệm", "No experience required"),
    ("under_1y", "Dưới 1 năm", "Under 1 year"),
    ("1y", "1 năm", "1 year"),
    ("2y", "2 năm", "2 years"),
    ("3y", "3 năm", "3 years"),
    ("4y", "4 năm", "4 years"),
    ("5y", "5 năm", "5 years"),
    ("over_5y", "Trên 5 năm", "Over 5 years"),
]

SENIORITY = [
    ("intern", "Thực tập sinh", "Intern"),
    ("staff", "Nhân viên", "Staff"),
    ("specialist", "Chuyên viên", "Specialist"),
    ("senior_specialist", "Chuyên viên cao cấp", "Senior Specialist"),
    ("team_lead", "Trưởng nhóm", "Team Lead"),
    ("department_head", "Trưởng/Phó phòng", "Department Head/Deputy"),
    ("manager_supervisor", "Quản lý/Giám sát", "Manager/Supervisor"),
    ("branch_head", "Trưởng chi nhánh", "Branch Head"),
    ("deputy_director", "Phó giám đốc", "Deputy Director"),
    ("director", "Giám đốc", "Director"),
    ("c_level", "Tổng giám đốc/C-level", "CEO/C-level"),
]

EMPLOYMENT_TYPE = [
    ("full_time", "Toàn thời gian", "Full-time"),
    ("part_time", "Bán thời gian", "Part-time"),
    ("internship", "Thực tập", "Internship"),
    ("seasonal", "Thời vụ", "Seasonal"),
    ("fixed_term_contract", "Hợp đồng có thời hạn", "Fixed-term contract"),
    ("freelance", "Freelance", "Freelance"),
    ("project_based", "Theo dự án", "Project-based"),
    ("other", "Khác", "Other"),
]

WORK_ARRANGEMENT = [
    ("onsite", "Làm việc tại văn phòng", "Office-based"),
    ("hybrid", "Hybrid", "Hybrid"),
    ("remote", "Remote", "Remote"),
    ("field", "Làm việc tại hiện trường", "Field-based"),
    ("frequent_travel", "Đi công tác thường xuyên", "Frequent travel"),
    ("shift", "Làm việc theo ca", "Shift work"),
]

SATURDAY_WORK = [
    ("works_saturday", "Làm thứ Bảy", "Works Saturday"),
    ("off_saturday", "Nghỉ thứ Bảy", "Saturday off"),
    ("not_mentioned", "Tin đăng không đề cập", "Not mentioned in posting"),
]

WORK_SCHEDULE = [
    ("mon_fri", "Thứ Hai–Thứ Sáu", "Mon–Fri"),
    ("mon_sat_morning", "Thứ Hai–Sáng thứ Bảy", "Mon–Sat morning"),
    ("mon_sat", "Thứ Hai–Thứ Bảy", "Mon–Sat"),
    ("shift_based", "Làm theo ca", "Shift-based"),
    ("office_shift", "Ca hành chính", "Office shift"),
    ("night_shift", "Ca đêm", "Night shift"),
    ("flexible", "Lịch linh hoạt", "Flexible schedule"),
    ("rotating_shift", "Xoay ca", "Rotating shift"),
    ("fixed_day_off", "Nghỉ cố định", "Fixed day off"),
    ("rotating_day_off", "Nghỉ luân phiên", "Rotating day off"),
]

SALARY_UNIT = [
    ("vnd_month", "VND/tháng", "VND/month"),
    ("usd_month", "USD/tháng", "USD/month"),
    ("vnd_hour", "VND/giờ", "VND/hour"),
    ("vnd_day", "VND/ngày", "VND/day"),
    ("vnd_project", "VND/dự án", "VND/project"),
]

COMPANY_INDUSTRY = [
    ("manufacturing", "Sản xuất", "Manufacturing"),
    ("textile_footwear", "Dệt may/Da giày", "Textile/Footwear"),
    ("food_fmcg", "Thực phẩm/FMCG", "Food/FMCG"),
    ("retail", "Bán lẻ", "Retail"),
    ("ecommerce", "Thương mại điện tử", "E-commerce"),
    ("tech_software", "Công nghệ/Phần mềm", "Technology/Software"),
    ("electronics_refrigeration", "Điện tử/Điện lạnh", "Electronics/Refrigeration"),
    ("mechanical_automation", "Cơ khí/Tự động hóa", "Mechanical/Automation"),
    ("construction", "Xây dựng", "Construction"),
    ("real_estate", "Bất động sản", "Real Estate"),
    ("banking", "Ngân hàng", "Banking"),
    ("finance", "Tài chính", "Finance"),
    ("securities", "Chứng khoán", "Securities"),
    ("insurance", "Bảo hiểm", "Insurance"),
    ("logistics_transport", "Logistics/Vận tải", "Logistics/Transport"),
    ("import_export", "Xuất nhập khẩu", "Import/Export"),
    ("education_training", "Giáo dục/Đào tạo", "Education/Training"),
    ("healthcare_pharma", "Y tế/Dược phẩm", "Healthcare/Pharma"),
    ("restaurant_hotel", "Nhà hàng/Khách sạn", "Restaurant/Hotel"),
    ("marketing_media", "Marketing/Truyền thông", "Marketing/Media"),
    ("consulting", "Tư vấn", "Consulting"),
    ("agriculture", "Nông nghiệp", "Agriculture"),
    ("energy_environment", "Năng lượng/Môi trường", "Energy/Environment"),
    ("other", "Khác", "Other"),
]

_TAXONOMIES = {
    "category_l1": CATEGORY_L1,
    "experience_level": EXPERIENCE_LEVEL,
    "seniority": SENIORITY,
    "employment_type": EMPLOYMENT_TYPE,
    "work_arrangement": WORK_ARRANGEMENT,
    "saturday_work": SATURDAY_WORK,
    "work_schedule": WORK_SCHEDULE,
    "salary_unit": SALARY_UNIT,
    "company_industry": COMPANY_INDUSTRY,
}


def allowed_slugs(field: str) -> set[str]:
    """Valid stored slugs for one of the fixed-enum Job fields above."""
    return {slug for slug, _vn, _en in _TAXONOMIES[field]}
