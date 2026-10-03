"""
Skills Taxonomy and Canonical Normalizer.
Provides comprehensive taxonomy indexing, alias resolution, and skill extraction.
"""

import re
from typing import Dict, List, Set, Tuple
from backend.app.schemas.profile import SkillItem

# Curated taxonomy: Category -> List of canonical skill names
SKILLS_TAXONOMY: Dict[str, List[str]] = {
    "Programming Languages": [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
        "Ruby", "PHP", "SQL", "HTML5", "CSS3", "Kotlin", "Swift", "R", "Scala", "Dart"
    ],
    "Frameworks & Libraries": [
        "FastAPI", "Django", "Flask", "React", "Angular", "Vue.js", "Next.js",
        "Node.js", "Express.js", "Spring Boot", ".NET Core", "PyTorch", "TensorFlow",
        "Scikit-Learn", "Pandas", "NumPy", "Tailwind CSS", "Bootstrap", "GraphQL"
    ],
    "Cloud & DevOps": [
        "Amazon Web Services (AWS)", "Microsoft Azure", "Google Cloud Platform (GCP)",
        "Docker", "Kubernetes", "CI/CD", "Terraform", "Linux", "Git", "GitHub Actions",
        "Jenkins", "Ansible", "Nginx", "Helm", "Prometheus", "Grafana"
    ],
    "Databases & Storage": [
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Elasticsearch",
        "DynamoDB", "Snowflake", "Cassandra", "ChromaDB", "Pinecone", "Milvus", "Firebase"
    ],
    "AI, ML & Data Engineering": [
        "Machine Learning", "Deep Learning", "Natural Language Processing (NLP)",
        "Large Language Models (LLMs)", "Retrieval-Augmented Generation (RAG)",
        "Vector Databases", "Computer Vision", "Data Engineering", "Data Modeling",
        "ETL Pipelines", "Apache Spark", "Apache Kafka", "Hugging Face"
    ],
    "Software Engineering & Architecture": [
        "REST APIs", "Microservices", "System Design", "Object-Oriented Programming (OOP)",
        "Test-Driven Development (TDD)", "Clean Code", "Design Patterns", "Unit Testing",
        "API Design", "Event-Driven Architecture"
    ],
    "Methodologies & Professional Skills": [
        "Agile", "Scrum", "Kanban", "Technical Leadership", "Project Management",
        "Code Review", "Cross-Functional Collaboration", "Problem Solving",
        "Technical Documentation", "Mentoring"
    ]
}

# Alias mapping: lowercase alias -> (canonical_name, category)
CANONICAL_ALIASES: Dict[str, Tuple[str, str]] = {
    "js": ("JavaScript", "Programming Languages"),
    "ts": ("TypeScript", "Programming Languages"),
    "py": ("Python", "Programming Languages"),
    "python3": ("Python", "Programming Languages"),
    "golang": ("Go", "Programming Languages"),
    "csharp": ("C#", "Programming Languages"),
    "c sharp": ("C#", "Programming Languages"),
    "c++": ("C++", "Programming Languages"),
    "cpp": ("C++", "Programming Languages"),
    "k8s": ("Kubernetes", "Cloud & DevOps"),
    "aws": ("Amazon Web Services (AWS)", "Cloud & DevOps"),
    "gcp": ("Google Cloud Platform (GCP)", "Cloud & DevOps"),
    "azure": ("Microsoft Azure", "Cloud & DevOps"),
    "postgres": ("PostgreSQL", "Databases & Storage"),
    "postgresql": ("PostgreSQL", "Databases & Storage"),
    "mongo": ("MongoDB", "Databases & Storage"),
    "tf": ("TensorFlow", "Frameworks & Libraries"),
    "ml": ("Machine Learning", "AI, ML & Data Engineering"),
    "dl": ("Deep Learning", "AI, ML & Data Engineering"),
    "nlp": ("Natural Language Processing (NLP)", "AI, ML & Data Engineering"),
    "llm": ("Large Language Models (LLMs)", "AI, ML & Data Engineering"),
    "llms": ("Large Language Models (LLMs)", "AI, ML & Data Engineering"),
    "rag": ("Retrieval-Augmented Generation (RAG)", "AI, ML & Data Engineering"),
    "rest": ("REST APIs", "Software Engineering & Architecture"),
    "restful": ("REST APIs", "Software Engineering & Architecture"),
    "rest api": ("REST APIs", "Software Engineering & Architecture"),
    "rest apis": ("REST APIs", "Software Engineering & Architecture"),
    "ci/cd": ("CI/CD", "Cloud & DevOps"),
    "cicd": ("CI/CD", "Cloud & DevOps"),
    "gh actions": ("GitHub Actions", "Cloud & DevOps"),
    "tdd": ("Test-Driven Development (TDD)", "Software Engineering & Architecture"),
    "oop": ("Object-Oriented Programming (OOP)", "Software Engineering & Architecture"),
}

# Pre-populate exact canonicals into the alias dictionary
for cat, skills in SKILLS_TAXONOMY.items():
    for skill in skills:
        key = skill.lower()
        if key not in CANONICAL_ALIASES:
            CANONICAL_ALIASES[key] = (skill, cat)


def get_canonical_skill(skill_name: str) -> Tuple[str, str]:
    """
    Resolves any skill alias to its canonical name and category.
    """
    clean = skill_name.strip().lower()
    if clean in CANONICAL_ALIASES:
        return CANONICAL_ALIASES[clean]
    return (skill_name.strip(), "General")


def extract_skills_from_text(text: str) -> List[SkillItem]:
    """
    Scans document text with regex boundary detection to extract canonical skills.
    Avoids false positives (e.g. matching 'Go' inside 'good').
    """
    if not text:
        return []

    found_skills: Dict[str, SkillItem] = {}

    for alias, (canonical, category) in CANONICAL_ALIASES.items():
        # Handle symbols in skills like C++, C#, .NET
        if alias in {"c++", "cpp"}:
            pattern = r"(?i)(?:\bC\+\+\b|\bCPP\b)"
        elif alias in {"c#", "csharp"}:
            pattern = r"(?i)(?:\bC#\b|\bCSharp\b)"
        elif alias == ".net core":
            pattern = r"(?i)(?:\.NET\s*Core|\bDOTNET\b)"
        elif alias in {"go", "r"}:
            pattern = rf"\b{re.escape(alias.upper())}\b"
        else:
            pattern = rf"(?i)\b{re.escape(alias)}\b"

        match = re.search(pattern, text)
        if match:
            # Capture contextual evidence sentence
            start = max(0, match.start() - 60)
            end = min(len(text), match.end() + 60)
            evidence = text[start:end].replace("\n", " ").strip()

            if canonical not in found_skills:
                found_skills[canonical] = SkillItem(
                    name=canonical,
                    category=category,
                    evidence=f"...{evidence}..." if (start > 0 or end < len(text)) else evidence,
                    level="Intermediate",
                )

    return list(found_skills.values())
