# Applicant Tracking System (ATS) Optimization Standards

## 1. ATS Architecture and Keyword Parsing
Modern Applicant Tracking Systems (e.g. Workday, Greenhouse, Lever, Taleo) extract candidate resumes into semi-structured database profiles before human recruiters review them. The ATS pipeline performs three primary operations:
1. **Document Text Extraction:** Converts PDF or DOCX binary formats into text tokens.
2. **Section Chunking & Heading Classification:** Maps document parts to standard candidate sections: Summary, Work Experience, Education, Technical Skills, and Certifications.
3. **Keyword & Competency Scoring:** Measures exact match and semantic proximity between candidate tokens and Job Description requirements.

## 2. Formatting Risks That Cause ATS Rejection
To ensure reliable parsing across legacy and modern ATS engines:
- **Avoid Complex Tables:** Many older parsers read table cells row-by-row or column-by-column in arbitrary order, scrambling job titles and employment dates. Use standard tabbed text or clean single-column layouts.
- **Avoid Multi-Column Layouts in PDFs:** Two-column PDFs often lead to interleaved sentences where the left column text merges horizontally into the right column.
- **Do Not Put Contact Details in Headers/Footers:** Many PDF text extractors strip top/bottom page margin regions entirely. Place full name, email, phone, location, and LinkedIn URL in the main document body.
- **Avoid Image-Based Text or Infographics:** Skill meters (e.g. 4/5 stars or colored progress bars) and icons are invisible to ATS scanners. Always represent technical competencies as plain text names.

## 3. High-Scoring Section Headings
Use recognizable, standard section headers:
- `Professional Experience` or `Work Experience`
- `Technical Skills` or `Core Competencies`
- `Education`
- `Certifications & Licenses`
- `Projects`
