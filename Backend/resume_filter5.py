# Enhanced AutoGen Resume Filtering System with Duplicate Detection
# Complete working code with all features integrated

import autogen
import os
import json
import PyPDF2
import docx
import numpy as np
from typing import List, Dict, Tuple, Optional, Any, Set
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import spacy
from datetime import datetime
import pandas as pd
from pathlib import Path
import re
import hashlib
import time
from difflib import SequenceMatcher
from collections import defaultdict
import phonenumbers
from fuzzywuzzy import fuzz
import jellyfish

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration for OpenAI API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Validate API key
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables!")

# Configuration for OpenAI with AutoGen
config_list = [
    {
        "model": OPENAI_MODEL,
        "api_key": OPENAI_API_KEY,
        "base_url": "https://api.openai.com/v1",
        "api_type": "openai"
    }
]

# For basic/faster operations
config_list_basic = [
    {
        "model": "gpt-3.5-turbo",
        "api_key": OPENAI_API_KEY,
        "base_url": "https://api.openai.com/v1",
        "api_type": "openai"
    }
]


class ResumeExtractor:
    """Extract text from various resume formats"""
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
            return ""
    
    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            print(f"Error reading DOCX {file_path}: {e}")
            return ""
    
    @staticmethod
    def extract_text(file_path: Path) -> str:
        """Extract text from resume file"""
        file_path_str = str(file_path)
        
        if file_path.suffix.lower() == '.pdf':
            return ResumeExtractor.extract_text_from_pdf(file_path_str)
        elif file_path.suffix.lower() in ['.docx', '.doc']:
            return ResumeExtractor.extract_text_from_docx(file_path_str)
        elif file_path.suffix.lower() == '.txt':
            with open(file_path_str, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return ""


class DuplicateCandidateDetector:
    """Advanced duplicate candidate detection system"""
    
    def __init__(self):
        self.candidates_db = {}
        self.email_to_id = {}
        self.phone_to_id = {}
        self.name_variations = defaultdict(set)
        
    def extract_candidate_identifiers(self, resume_text: str, filename: str) -> Dict:
        """Extract all possible identifiers from resume"""
        identifiers = {
            'filename': filename,
            'emails': self._extract_emails(resume_text),
            'phones': self._extract_phones(resume_text),
            'names': self._extract_names(resume_text),
            'github': self._extract_github(resume_text),
            'linkedin': self._extract_linkedin(resume_text),
            'content_hash': self._generate_content_hash(resume_text),
            'education_hash': self._generate_education_hash(resume_text),
            'experience_hash': self._generate_experience_hash(resume_text)
        }
        return identifiers
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extract and validate email addresses"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        valid_emails = []
        for email in emails:
            # Basic validation and normalization
            email_lower = email.lower()
            # Filter out common non-email patterns
            if not any(invalid in email_lower for invalid in ['example.com', 'test.com', '@gmail.co']):
                valid_emails.append(email_lower)
                
        return list(set(valid_emails))
    
    def _extract_phones(self, text: str) -> List[str]:
        """Extract and normalize phone numbers"""
        # Multiple phone patterns
        phone_patterns = [
            r'\+?1?\s*\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})',  # US format
            r'\+?(\d{1,3})[\s.-]?(\d{3,4})[\s.-]?(\d{3,4})[\s.-]?(\d{3,4})',  # International
            r'\b(\d{10})\b',  # 10 digit number
            r'\+91[\s.-]?(\d{10})',  # Indian format
        ]
        
        phones = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    phone = ''.join(match)
                else:
                    phone = match
                
                # Remove non-digits
                phone_digits = re.sub(r'\D', '', phone)
                
                # Normalize to last 10 digits (removing country codes)
                if len(phone_digits) >= 10:
                    normalized = phone_digits[-10:]
                    phones.append(normalized)
        
        return list(set(phones))
    
    def _extract_names(self, text: str) -> List[str]:
        """Extract potential names from resume"""
        names = []
        
        # Look for name patterns at the beginning of resume
        lines = text.split('\n')
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            line = line.strip()
            
            # Skip empty lines and common headers
            if not line or any(keyword in line.lower() for keyword in 
                             ['resume', 'curriculum', 'cv', 'objective', 'summary']):
                continue
            
            # Check if line could be a name (2-4 words, title case)
            words = line.split()
            if 2 <= len(words) <= 4:
                if all(word[0].isupper() for word in words if word):
                    names.append(line)
        
        # Also look for "Name:" pattern
        name_pattern = r'(?:Name|NAME|name)\s*[:|-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        name_matches = re.findall(name_pattern, text)
        names.extend(name_matches)
        
        return list(set(names))
    
    def _extract_github(self, text: str) -> Optional[str]:
        """Extract GitHub username"""
        github_patterns = [
            r'github\.com/([a-zA-Z0-9-]+)',
            r'github\s*:\s*([a-zA-Z0-9-]+)',
            r'@([a-zA-Z0-9-]+)\s*\(github\)',
        ]
        
        for pattern in github_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).lower()
        return None
    
    def _extract_linkedin(self, text: str) -> Optional[str]:
        """Extract LinkedIn profile ID"""
        linkedin_patterns = [
            r'linkedin\.com/in/([a-zA-Z0-9-]+)',
            r'linkedin\s*:\s*([a-zA-Z0-9-]+)',
        ]
        
        for pattern in linkedin_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).lower()
        return None
    
    def _generate_content_hash(self, text: str) -> str:
        """Generate hash of key content (excluding name)"""
        # Remove potential name lines (first few lines)
        lines = text.split('\n')
        content_lines = lines[5:] if len(lines) > 5 else lines
        
        # Remove emails and phones to focus on content
        content = '\n'.join(content_lines)
        content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', content)
        content = re.sub(r'\+?1?\s*\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})', '', content)
        
        # Normalize whitespace
        content = ' '.join(content.split())
        
        return hashlib.md5(content.encode()).hexdigest()
    
    def _generate_education_hash(self, text: str) -> str:
        """Generate hash based on education details"""
        education_section = self._extract_section(text, ['education', 'academic', 'qualification'])
        
        # Extract degree and institution patterns
        degree_patterns = [
            r'(B\.?S\.?|B\.?Sc\.?|Bachelor|B\.?Tech|B\.?E\.?)',
            r'(M\.?S\.?|M\.?Sc\.?|Master|M\.?Tech|MBA|M\.?E\.?)',
            r'(Ph\.?D\.?|Doctorate)',
        ]
        
        institutions = []
        degrees = []
        
        for pattern in degree_patterns:
            matches = re.findall(pattern, education_section, re.IGNORECASE)
            degrees.extend(matches)
        
        # Extract years
        years = re.findall(r'\b(19\d{2}|20\d{2})\b', education_section)
        
        # Create normalized education string
        edu_string = ' '.join(sorted(degrees + years))
        return hashlib.md5(edu_string.encode()).hexdigest()[:16]
    
    def _generate_experience_hash(self, text: str) -> str:
        """Generate hash based on work experience"""
        experience_section = self._extract_section(text, ['experience', 'employment', 'work history'])
        
        # Extract company names (capitalized words that might be companies)
        companies = re.findall(r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b', experience_section)
        
        # Extract years
        years = re.findall(r'\b(19\d{2}|20\d{2})\b', experience_section)
        
        # Extract key technologies
        tech_keywords = ['python', 'java', 'javascript', 'sql', 'aws', 'docker', 'kubernetes']
        techs_found = [tech for tech in tech_keywords if tech in experience_section.lower()]
        
        # Create normalized experience string
        exp_string = ' '.join(sorted(companies[:5] + years + techs_found))
        return hashlib.md5(exp_string.encode()).hexdigest()[:16]
    
    def _extract_section(self, text: str, section_keywords: List[str]) -> str:
        """Extract a section from resume based on keywords"""
        lines = text.split('\n')
        section_start = -1
        section_lines = []
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Check if this line starts our section
            if any(keyword in line_lower for keyword in section_keywords):
                section_start = i
                continue
            
            # If we're in a section, collect lines
            if section_start >= 0:
                # Check if we hit another section
                if any(keyword in line_lower for keyword in 
                      ['experience', 'education', 'skills', 'projects', 'summary', 'objective']):
                    if not any(keyword in line_lower for keyword in section_keywords):
                        break
                
                section_lines.append(line)
        
        return '\n'.join(section_lines)
    
    def calculate_similarity_score(self, id1: Dict, id2: Dict) -> Dict[str, float]:
        """Calculate similarity scores between two candidates"""
        scores = {
            'email_match': 0.0,
            'phone_match': 0.0,
            'name_similarity': 0.0,
            'github_match': 0.0,
            'linkedin_match': 0.0,
            'content_similarity': 0.0,
            'education_match': 0.0,
            'experience_match': 0.0
        }
        
        # Email match (exact)
        if id1['emails'] and id2['emails']:
            if set(id1['emails']) & set(id2['emails']):
                scores['email_match'] = 1.0
        
        # Phone match (exact)
        if id1['phones'] and id2['phones']:
            if set(id1['phones']) & set(id2['phones']):
                scores['phone_match'] = 1.0
        
        # Name similarity
        if id1['names'] and id2['names']:
            max_similarity = 0.0
            for name1 in id1['names']:
                for name2 in id2['names']:
                    # Fuzzy matching
                    fuzzy_score = fuzz.token_sort_ratio(name1.lower(), name2.lower()) / 100.0
                    
                    # Phonetic matching
                    try:
                        phonetic_score = 1.0 if jellyfish.soundex(name1) == jellyfish.soundex(name2) else 0.0
                    except:
                        phonetic_score = 0.0
                    
                    # Check if one name contains the other (nickname/shortened name)
                    contains_score = 0.8 if (name1.lower() in name2.lower() or 
                                           name2.lower() in name1.lower()) else 0.0
                    
                    similarity = max(fuzzy_score, phonetic_score, contains_score)
                    max_similarity = max(max_similarity, similarity)
            
            scores['name_similarity'] = max_similarity
        
        # GitHub match
        if id1['github'] and id2['github']:
            scores['github_match'] = 1.0 if id1['github'] == id2['github'] else 0.0
        
        # LinkedIn match
        if id1['linkedin'] and id2['linkedin']:
            scores['linkedin_match'] = 1.0 if id1['linkedin'] == id2['linkedin'] else 0.0
        
        # Content similarity
        if id1['content_hash'] == id2['content_hash']:
            scores['content_similarity'] = 1.0
        
        # Education match
        if id1['education_hash'] == id2['education_hash']:
            scores['education_match'] = 0.8
        
        # Experience match
        if id1['experience_hash'] == id2['experience_hash']:
            scores['experience_match'] = 0.8
        
        return scores
    
    def is_duplicate(self, scores: Dict[str, float]) -> Tuple[bool, float, str]:
        """Determine if two candidates are duplicates based on scores"""
        
        # Definite duplicates (any exact identifier match)
        if scores['email_match'] == 1.0:
            return True, 1.0, "Same email address"
        
        if scores['phone_match'] == 1.0:
            return True, 0.95, "Same phone number"
        
        if scores['github_match'] == 1.0:
            return True, 0.95, "Same GitHub account"
        
        if scores['linkedin_match'] == 1.0:
            return True, 0.95, "Same LinkedIn profile"
        
        # High probability duplicates
        if scores['content_similarity'] == 1.0:
            return True, 0.9, "Identical resume content"
        
        # Combination scoring for probable duplicates
        weighted_score = (
            scores['name_similarity'] * 0.2 +
            scores['education_match'] * 0.3 +
            scores['experience_match'] * 0.3 +
            scores['content_similarity'] * 0.2
        )
        
        # If name is similar AND education/experience match
        if (scores['name_similarity'] > 0.7 and 
            scores['education_match'] > 0.7 and 
            scores['experience_match'] > 0.7):
            return True, weighted_score, "High similarity in name, education, and experience"
        
        # If very high overall similarity
        if weighted_score > 0.85:
            return True, weighted_score, "Very high overall similarity"
        
        return False, weighted_score, "Not duplicate"
    
    def add_candidate(self, resume_text: str, filename: str) -> Tuple[str, List[Dict]]:
        """Add candidate and check for duplicates"""
        identifiers = self.extract_candidate_identifiers(resume_text, filename)
        
        # Check for duplicates
        duplicates = []
        
        # Check by email
        for email in identifiers['emails']:
            if email in self.email_to_id:
                existing_id = self.email_to_id[email]
                existing = self.candidates_db[existing_id]
                scores = self.calculate_similarity_score(identifiers, existing)
                is_dup, confidence, reason = self.is_duplicate(scores)
                if is_dup:
                    duplicates.append({
                        'candidate_id': existing_id,
                        'filename': existing['filename'],
                        'confidence': confidence,
                        'reason': reason,
                        'matched_by': 'email'
                    })
        
        # Check by phone
        for phone in identifiers['phones']:
            if phone in self.phone_to_id:
                existing_id = self.phone_to_id[phone]
                if not any(d['candidate_id'] == existing_id for d in duplicates):
                    existing = self.candidates_db[existing_id]
                    scores = self.calculate_similarity_score(identifiers, existing)
                    is_dup, confidence, reason = self.is_duplicate(scores)
                    if is_dup:
                        duplicates.append({
                            'candidate_id': existing_id,
                            'filename': existing['filename'],
                            'confidence': confidence,
                            'reason': reason,
                            'matched_by': 'phone'
                        })
        
        # Check all candidates for similarity (if no exact match found)
        if not duplicates:
            for cand_id, candidate in self.candidates_db.items():
                scores = self.calculate_similarity_score(identifiers, candidate)
                is_dup, confidence, reason = self.is_duplicate(scores)
                if is_dup:
                    duplicates.append({
                        'candidate_id': cand_id,
                        'filename': candidate['filename'],
                        'confidence': confidence,
                        'reason': reason,
                        'matched_by': 'similarity'
                    })
        
        # Generate unique ID
        candidate_id = hashlib.md5(f"{filename}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # Store candidate
        self.candidates_db[candidate_id] = identifiers
        
        # Update indexes
        for email in identifiers['emails']:
            self.email_to_id[email] = candidate_id
        
        for phone in identifiers['phones']:
            self.phone_to_id[phone] = candidate_id
        
        # Track name variations
        for name in identifiers['names']:
            self.name_variations[name.lower()].add(candidate_id)
        
        return candidate_id, duplicates
    
    def get_duplicate_groups(self) -> List[List[Dict]]:
        """Get groups of duplicate candidates with details"""
        groups = []
        processed = set()
        
        for cand_id in self.candidates_db:
            if cand_id in processed:
                continue
            
            group = [{'candidate_id': cand_id, 'filename': self.candidates_db[cand_id]['filename']}]
            processed.add(cand_id)
            
            # Find all related candidates
            candidate = self.candidates_db[cand_id]
            
            # Check by identifiers
            for email in candidate['emails']:
                for other_id in self.candidates_db:
                    if other_id != cand_id and other_id not in processed:
                        if email in self.candidates_db[other_id]['emails']:
                            group.append({
                                'candidate_id': other_id,
                                'filename': self.candidates_db[other_id]['filename']
                            })
                            processed.add(other_id)
            
            for phone in candidate['phones']:
                for other_id in self.candidates_db:
                    if other_id != cand_id and other_id not in processed:
                        if phone in self.candidates_db[other_id]['phones']:
                            group.append({
                                'candidate_id': other_id,
                                'filename': self.candidates_db[other_id]['filename']
                            })
                            processed.add(other_id)
            
            if len(group) > 1:
                groups.append(group)
        
        return groups


class DuplicateHandlingStrategy:
    """Strategies for handling duplicate candidates"""
    
    @staticmethod
    def merge_scores(candidates: List[Dict]) -> Dict:
        """Merge scores from duplicate candidates, taking the best scores"""
        if not candidates:
            return {}
        
        # Start with the first candidate
        merged = candidates[0].copy()
        
        # Track all filenames
        all_filenames = [c['filename'] for c in candidates]
        merged['all_filenames'] = all_filenames
        merged['duplicate_count'] = len(candidates)
        
        # Take the best scores
        for candidate in candidates[1:]:
            if candidate.get('final_score', 0) > merged.get('final_score', 0):
                merged['final_score'] = candidate['final_score']
            
            if candidate.get('skill_score', 0) > merged.get('skill_score', 0):
                merged['skill_score'] = candidate['skill_score']
                merged['matched_skills'] = candidate.get('matched_skills', [])
            
            if candidate.get('experience_score', 0) > merged.get('experience_score', 0):
                merged['experience_score'] = candidate['experience_score']
                merged['detected_experience_years'] = candidate.get('detected_experience_years', 0)
            
            if candidate.get('professional_development_score', 0) > merged.get('professional_development_score', 0):
                merged['professional_development_score'] = candidate['professional_development_score']
                merged['professional_development'] = candidate.get('professional_development', {})
        
        # Add duplicate warning
        merged['has_duplicates'] = True
        merged['duplicate_info'] = {
            'count': len(candidates),
            'filenames': all_filenames,
            'selected_filename': merged['filename']
        }
        
        return merged


class EnhancedJobTicket:
    """Enhanced JobTicket class that reads latest updates from JSON structure"""
    
    def __init__(self, ticket_folder: str):
        self.ticket_folder = Path(ticket_folder)
        self.ticket_id = self.ticket_folder.name
        self.raw_data = self._load_raw_data()
        self.job_details = self._merge_with_updates()
        self._print_loaded_details()
    
    def _load_raw_data(self) -> Dict:
        """Load the raw JSON data from the ticket folder"""
        # Look for job_details.json first
        priority_files = ['job_details.json', 'job-data.json', 'job.json']
        json_file = None
        
        for filename in priority_files:
            file_path = self.ticket_folder / filename
            if file_path.exists():
                json_file = file_path
                break
        
        # If no priority file found, look for any JSON except metadata.json
        if not json_file:
            json_files = [f for f in self.ticket_folder.glob("*.json") 
                         if f.name not in ['metadata.json', 'applications.json']]
            if json_files:
                json_file = json_files[0]
        
        if not json_file:
            # If only applications.json exists, use it as fallback
            app_file = self.ticket_folder / 'applications.json'
            if app_file.exists():
                json_file = app_file
            else:
                raise FileNotFoundError(f"No JSON file found in {self.ticket_folder}")
        
        print(f"📄 Loading job details from: {json_file.name}")
        
        # Load job description from txt file if exists
        job_desc_file = self.ticket_folder / 'job-description.txt'
        job_description_text = ""
        if job_desc_file.exists():
            print(f"📝 Loading job description from: job-description.txt")
            with open(job_desc_file, 'r', encoding='utf-8') as f:
                job_description_text = f.read()
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # If we loaded job description separately, add it to the data
            if job_description_text and isinstance(data, dict):
                if 'job_description' not in data:
                    data['job_description'] = job_description_text
                if 'job_details' in data and 'job_description' not in data['job_details']:
                    data['job_details']['job_description'] = job_description_text
            
            return data
        except Exception as e:
            print(f"❌ Error loading JSON: {e}")
            raise
    
    def _merge_with_updates(self) -> Dict:
        """Merge initial details with latest updates"""
        # Handle different JSON structures
        if isinstance(self.raw_data, list):
            # If it's a list of applications, create a job details structure
            print("📝 Detected applications list format, creating job structure...")
            merged_details = {
                'ticket_id': self.ticket_id,
                'applications': self.raw_data,
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                # Default job details - you may need to adjust these
                'job_title': 'Software Developer',
                'position': 'Software Developer',
                'experience_required': '2+ years',
                'location': 'Remote',
                'salary_range': 'Competitive',
                'required_skills': 'Python, JavaScript, SQL',
                'job_description': 'We are looking for a talented developer',
                'deadline': 'Open until filled'
            }
            return merged_details
        
        # Check if data has the structure from your job_details.json
        if 'ticket_info' in self.raw_data and 'job_details' in self.raw_data:
            # This matches your actual structure
            merged_details = self.raw_data['job_details'].copy()
            merged_details['ticket_id'] = self.raw_data['ticket_info'].get('ticket_id', self.ticket_id)
            merged_details['status'] = self.raw_data['ticket_info'].get('status', 'active')
            merged_details['created_at'] = self.raw_data['ticket_info'].get('created_at', '')
            merged_details['last_updated'] = self.raw_data.get('saved_at', '')
            return merged_details
        
        # Original logic for other formats
        if 'initial_details' in self.raw_data:
            merged_details = self.raw_data['initial_details'].copy()
        else:
            merged_details = self.raw_data.copy()
        
        merged_details['ticket_id'] = self.raw_data.get('ticket_id', self.ticket_id)
        merged_details['status'] = self.raw_data.get('status', 'unknown')
        merged_details['created_at'] = self.raw_data.get('created_at', '')
        merged_details['last_updated'] = self.raw_data.get('last_updated', '')
        
        if 'updates' in self.raw_data and self.raw_data['updates']:
            print(f"📝 Found {len(self.raw_data['updates'])} update(s)")
            
            sorted_updates = sorted(
                self.raw_data['updates'], 
                key=lambda x: x.get('timestamp', ''),
                reverse=True
            )
            
            latest_update = sorted_updates[0]
            print(f"✅ Applying latest update from: {latest_update.get('timestamp', 'unknown')}")
            
            if 'details' in latest_update:
                for key, value in latest_update['details'].items():
                    if value:
                        merged_details[key] = value
                        print(f"   Updated {key}: {value}")
        
        return merged_details
    
    def _print_loaded_details(self):
        """Print the loaded job details for verification"""
        print("\n" + "="*60)
        print("📋 LOADED JOB REQUIREMENTS")
        print("="*60)
        print(f"Position: {self.position}")
        print(f"Experience: {self.experience_required}")
        print(f"Location: {self.location}")
        print(f"Salary: {self.salary_range}")
        print(f"Skills: {', '.join(self.tech_stack)}")
        print(f"Deadline: {self.deadline}")
        print(f"Last Updated: {self.job_details.get('last_updated', 'Unknown')}")
        print("="*60 + "\n")
    
    def _parse_skills(self, skills_str: str) -> List[str]:
        """Parse skills from string format to list"""
        if isinstance(skills_str, list):
            return skills_str
        
        if not skills_str:
            return []
        
        skills = re.split(r'[,;|]\s*', skills_str)
        expanded_skills = []
        
        for skill in skills:
            if '(' in skill and ')' in skill:
                main_skill = skill[:skill.index('(')].strip()
                variations = skill[skill.index('(')+1:skill.index(')')].strip()
                expanded_skills.append(main_skill)
                if '/' in variations:
                    expanded_skills.extend([v.strip() for v in variations.split('/')])
                else:
                    expanded_skills.append(variations)
            else:
                expanded_skills.append(skill.strip())
        
        return list(set([s for s in expanded_skills if s]))
    
    @property
    def position(self) -> str:
        return (self.job_details.get('job_title') or 
                self.job_details.get('position') or 
                self.job_details.get('title', 'Unknown Position'))
    
    @property
    def experience_required(self) -> str:
        return (self.job_details.get('experience_required') or 
                self.job_details.get('experience') or 
                self.job_details.get('years_of_experience', '0+ years'))
    
    @property
    def location(self) -> str:
        return self.job_details.get('location', 'Not specified')
    
    @property
    def salary_range(self) -> str:
        salary = self.job_details.get('salary_range', '')
        if isinstance(salary, dict):
            min_sal = salary.get('min', '')
            max_sal = salary.get('max', '')
            currency = salary.get('currency', 'INR')
            return f"{currency} {min_sal}-{max_sal}"
        return salary or 'Not specified'
    
    @property
    def deadline(self) -> str:
        return self.job_details.get('deadline', 'Not specified')
    
    @property
    def tech_stack(self) -> List[str]:
        skills = self.job_details.get('required_skills') or self.job_details.get('tech_stack', '')
        return self._parse_skills(skills)
    
    @property
    def requirements(self) -> List[str]:
        requirements = []
        
        if self.job_details.get('job_description'):
            requirements.append(self.job_details['job_description'])
        
        req_field = self.job_details.get('requirements', [])
        if isinstance(req_field, str):
            requirements.extend([r.strip() for r in req_field.split('\n') if r.strip()])
        elif isinstance(req_field, list):
            requirements.extend(req_field)
        
        return requirements
    
    @property
    def description(self) -> str:
        return (self.job_details.get('job_description') or 
                self.job_details.get('description') or 
                self.job_details.get('summary', ''))
    
    @property
    def employment_type(self) -> str:
        return self.job_details.get('employment_type', 'Full-time')
    
    @property
    def nice_to_have(self) -> List[str]:
        nice = (self.job_details.get('nice_to_have') or 
                self.job_details.get('preferred_skills') or 
                self.job_details.get('bonus_skills', []))
        
        if isinstance(nice, str):
            return [n.strip() for n in nice.split('\n') if n.strip()]
        elif isinstance(nice, list):
            return nice
        return []
    
    def get_resumes(self) -> List[Path]:
        """Get all resume files from the ticket folder"""
        resume_extensions = ['.pdf', '.docx', '.doc']  # Removed .txt to avoid job descriptions
        resumes = []
        
        for ext in resume_extensions:
            resumes.extend(self.ticket_folder.glob(f"*{ext}"))
        
        # Expanded exclusion list
        excluded_keywords = ['job_description', 'job-description', 'requirements', 'jd', 'job_posting', 'job-posting']
        filtered_resumes = []
        
        for resume in resumes:
            # Check if file name contains any excluded keyword
            if not any(keyword in resume.name.lower().replace('_', '-') for keyword in excluded_keywords):
                filtered_resumes.append(resume)
            else:
                print(f"   ℹ️ Excluding non-resume file: {resume.name}")
        
        return filtered_resumes


class ProfessionalDevelopmentScorer:
    """Score candidates based on continuous learning and professional development"""
    
    def __init__(self):
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        
        # Comprehensive certification database with categories and recency importance
        self.certifications_db = {
            'cloud': {
                'aws': {
                    'patterns': [
                        'aws certified solutions architect', 'aws certified developer',
                        'aws certified sysops', 'aws certified devops', 'aws certified security',
                        'aws certified database', 'aws certified machine learning',
                        'aws certified data analytics', 'aws solutions architect',
                        'amazon web services certified', 'aws certification'
                    ],
                    'weight': 1.0,
                    'recency_important': True
                },
                'azure': {
                    'patterns': [
                        'azure certified', 'azure fundamentals', 'azure administrator',
                        'azure developer', 'azure solutions architect', 'azure devops',
                        'azure data engineer', 'azure ai engineer', 'microsoft certified azure',
                        'az-900', 'az-104', 'az-204', 'az-303', 'az-304', 'az-400'
                    ],
                    'weight': 1.0,
                    'recency_important': True
                },
                'gcp': {
                    'patterns': [
                        'google cloud certified', 'gcp certified', 'google cloud professional',
                        'cloud architect google', 'cloud engineer google', 'data engineer google',
                        'google cloud developer', 'google cloud network engineer'
                    ],
                    'weight': 1.0,
                    'recency_important': True
                }
            },
            'data': {
                'general': {
                    'patterns': [
                        'databricks certified', 'cloudera certified', 'hortonworks certified',
                        'mongodb certified', 'cassandra certified', 'elastic certified',
                        'confluent certified', 'snowflake certified', 'tableau certified',
                        'power bi certified', 'qlik certified'
                    ],
                    'weight': 0.9,
                    'recency_important': True
                }
            },
            'programming': {
                'general': {
                    'patterns': [
                        'oracle certified java', 'microsoft certified c#', 'python institute certified',
                        'javascript certified', 'golang certified', 'rust certified',
                        'scala certified', 'kotlin certified'
                    ],
                    'weight': 0.8,
                    'recency_important': True
                }
            },
            'devops': {
                'general': {
                    'patterns': [
                        'docker certified', 'kubernetes certified', 'cka', 'ckad', 'cks',
                        'jenkins certified', 'ansible certified', 'terraform certified',
                        'gitlab certified', 'github actions certified'
                    ],
                    'weight': 0.9,
                    'recency_important': True
                }
            },
            'security': {
                'general': {
                    'patterns': [
                        'cissp', 'ceh', 'certified ethical hacker', 'comptia security+',
                        'comptia pentest+', 'gsec', 'gcih', 'oscp', 'security certified'
                    ],
                    'weight': 0.85,
                    'recency_important': True
                }
            },
            'agile': {
                'general': {
                    'patterns': [
                        'certified scrum master', 'csm', 'psm', 'safe certified',
                        'pmp', 'prince2', 'agile certified', 'kanban certified',
                        'product owner certified', 'cspo'
                    ],
                    'weight': 0.7,
                    'recency_important': False
                }
            },
            'ai_ml': {
                'general': {
                    'patterns': [
                        'tensorflow certified', 'pytorch certified', 'deep learning certified',
                        'machine learning certified', 'ai certified', 'coursera deep learning',
                        'fast.ai certified', 'nvidia certified'
                    ],
                    'weight': 0.95,
                    'recency_important': True
                }
            }
        }
        
        # Online learning platforms
        self.learning_platforms = {
            'premium': {
                'patterns': ['coursera', 'udacity', 'edx', 'pluralsight', 'linkedin learning', 
                           'datacamp', 'udemy business', 'o\'reilly', 'safari books'],
                'weight': 0.8
            },
            'standard': {
                'patterns': ['udemy', 'skillshare', 'khan academy', 'codecademy', 
                           'freecodecamp', 'w3schools'],
                'weight': 0.6
            },
            'specialized': {
                'patterns': ['fast.ai', 'deeplearning.ai', 'kaggle learn', 'qwiklabs',
                           'linux academy', 'cloud academy', 'acloud.guru'],
                'weight': 0.9
            }
        }
        
        # Conference and event patterns
        self.conference_patterns = {
            'speaking': {
                'patterns': [
                    'speaker at', 'presented at', 'talk at', 'keynote', 'panelist',
                    'conference speaker', 'tech talk', 'lightning talk', 'workshop facilitator'
                ],
                'weight': 1.0
            },
            'attendance': {
                'patterns': [
                    'attended', 'participant', 'conference attendee', 'summit participant',
                    'bootcamp', 'workshop attended', 'training attended'
                ],
                'weight': 0.5
            },
            'major_conferences': {
                'patterns': [
                    're:invent', 'google i/o', 'microsoft build', 'kubecon', 'pycon',
                    'jsconf', 'defcon', 'black hat', 'rsa conference', 'strata',
                    'spark summit', 'kafka summit', 'dockercon', 'hashiconf'
                ],
                'weight': 0.8
            }
        }
        
        # Content creation patterns
        self.content_creation = {
            'blog': {
                'patterns': [
                    'blog', 'medium.com', 'dev.to', 'hashnode', 'technical blog',
                    'tech blogger', 'write about', 'published articles', 'technical writing'
                ],
                'weight': 0.8
            },
            'video': {
                'patterns': [
                    'youtube channel', 'video tutorials', 'screencast', 'tech videos',
                    'online instructor', 'course creator'
                ],
                'weight': 0.9
            },
            'open_source': {
                'patterns': [
                    'github.com', 'gitlab.com', 'bitbucket', 'open source contributor',
                    'maintainer', 'pull requests', 'github stars', 'npm package',
                    'pypi package', 'maven package'
                ],
                'weight': 1.0
            },
            'community': {
                'patterns': [
                    'stack overflow', 'stackoverflow reputation', 'forum moderator',
                    'discord community', 'slack community', 'reddit moderator',
                    'community leader', 'meetup organizer'
                ],
                'weight': 0.7
            }
        }
    
    def extract_years_from_text(self, text: str, keyword: str, look_ahead: int = 50) -> List[int]:
        """Extract years mentioned near a keyword"""
        years_found = []
        keyword_indices = [m.start() for m in re.finditer(keyword, text.lower())]
        
        for idx in keyword_indices:
            # Look ahead and behind the keyword for year patterns
            start = max(0, idx - 30)
            end = min(len(text), idx + len(keyword) + look_ahead)
            snippet = text[start:end]
            
            # Find 4-digit years between 2010 and current year + 1
            year_pattern = r'\b(20[1-2][0-9])\b'
            years = re.findall(year_pattern, snippet)
            years_found.extend([int(y) for y in years if 2010 <= int(y) <= self.current_year + 1])
        
        return years_found
    
    def calculate_recency_score(self, years: List[int]) -> float:
        """Calculate how recent the certifications/courses are"""
        if not years:
            return 0.5  # No year info, assume moderate recency
        
        most_recent = max(years)
        years_ago = self.current_year - most_recent
        
        if years_ago == 0:
            return 1.0  # Current year
        elif years_ago == 1:
            return 0.9  # Last year
        elif years_ago == 2:
            return 0.8  # 2 years ago
        elif years_ago == 3:
            return 0.6  # 3 years ago
        elif years_ago <= 5:
            return 0.4  # 4-5 years ago
        else:
            return 0.2  # Older than 5 years
    
    def score_certifications(self, resume_text: str) -> Dict[str, Any]:
        """Score professional certifications"""
        resume_lower = resume_text.lower()
        
        results = {
            'certification_score': 0.0,
            'certification_count': 0,
            'recent_certification_score': 0.0,
            'certifications_found': [],
            'certification_categories': {},
            'years_detected': []
        }
        
        # Track unique certifications to avoid double counting
        found_certs = set()
        category_scores = {}
        all_years = []
        
        # Search for certifications by category
        for category, cert_types in self.certifications_db.items():
            category_scores[category] = 0.0
            category_certs = []
            
            for cert_type, cert_info in cert_types.items():
                for pattern in cert_info['patterns']:
                    if pattern in resume_lower and pattern not in found_certs:
                        found_certs.add(pattern)
                        results['certification_count'] += 1
                        category_certs.append(pattern)
                        
                        # Extract years for recency
                        years = self.extract_years_from_text(resume_text, pattern)
                        all_years.extend(years)
                        
                        # Add to score with weight
                        category_scores[category] += cert_info['weight']
            
            if category_certs:
                results['certification_categories'][category] = category_certs
        
        # Calculate overall certification score
        if results['certification_count'] > 0:
            # Diminishing returns for multiple certs
            base_score = min(results['certification_count'] * 0.15, 0.6)
            
            # Category diversity bonus
            category_diversity = len(results['certification_categories']) / len(self.certifications_db)
            diversity_bonus = category_diversity * 0.2
            
            # High-value certification bonus
            high_value_bonus = 0.0
            if any(cat in results['certification_categories'] for cat in ['cloud', 'ai_ml', 'data']):
                high_value_bonus = 0.2
            
            results['certification_score'] = min(base_score + diversity_bonus + high_value_bonus, 1.0)
        
        # Calculate recency score
        if all_years:
            results['years_detected'] = sorted(list(set(all_years)), reverse=True)
            results['recent_certification_score'] = self.calculate_recency_score(all_years)
        
        results['certifications_found'] = list(found_certs)
        
        return results
    
    def score_online_learning(self, resume_text: str) -> Dict[str, Any]:
        """Score online course completions"""
        resume_lower = resume_text.lower()
        
        results = {
            'online_learning_score': 0.0,
            'platforms_found': [],
            'course_count_estimate': 0,
            'recent_learning_score': 0.0,
            'specializations_mentioned': False
        }
        
        platforms_detected = set()
        platform_weights = []
        
        # Detect learning platforms
        for tier, platform_info in self.learning_platforms.items():
            for platform in platform_info['patterns']:
                if platform in resume_lower:
                    platforms_detected.add(platform)
                    platform_weights.append(platform_info['weight'])
        
        results['platforms_found'] = list(platforms_detected)
        
        # Look for course completion indicators
        course_indicators = [
            r'completed?\s+\d+\s+courses?',
            r'\d+\s+courses?\s+completed',
            r'certification?\s+in',
            r'specialization\s+in',
            r'nanodegree',
            r'micromasters',
            r'professional certificate'
        ]
        
        course_count = 0
        for pattern in course_indicators:
            matches = re.findall(pattern, resume_lower)
            course_count += len(matches)
        
        # Check for specializations (higher value)
        if any(term in resume_lower for term in ['specialization', 'nanodegree', 'micromasters']):
            results['specializations_mentioned'] = True
            course_count += 2  # Specializations count as multiple courses
        
        results['course_count_estimate'] = course_count
        
        # Calculate score
        if platforms_detected:
            # Base score from platforms
            platform_score = sum(platform_weights) / len(platform_weights) if platform_weights else 0
            
            # Course quantity bonus
            course_bonus = min(course_count * 0.1, 0.3)
            
            # Specialization bonus
            spec_bonus = 0.2 if results['specializations_mentioned'] else 0
            
            results['online_learning_score'] = min(platform_score * 0.5 + course_bonus + spec_bonus, 1.0)
        
        # Check for recent learning
        recent_years = []
        for platform in platforms_detected:
            years = self.extract_years_from_text(resume_text, platform)
            recent_years.extend(years)
        
        if recent_years:
            results['recent_learning_score'] = self.calculate_recency_score(recent_years)
        
        return results
    
    def score_conference_participation(self, resume_text: str) -> Dict[str, Any]:
        """Score conference attendance and speaking"""
        resume_lower = resume_text.lower()
        
        results = {
            'conference_score': 0.0,
            'speaking_score': 0.0,
            'attendance_score': 0.0,
            'events_found': [],
            'speaker_events': [],
            'major_conferences': []
        }
        
        # Check for speaking engagements (high value)
        for pattern in self.conference_patterns['speaking']['patterns']:
            if pattern in resume_lower:
                results['speaker_events'].append(pattern)
                # Try to extract event names
                event_matches = re.findall(f'{pattern}[^.]*(?:conference|summit|meetup|workshop)', resume_lower)
                results['events_found'].extend(event_matches)
        
        # Check for conference attendance
        for pattern in self.conference_patterns['attendance']['patterns']:
            if pattern in resume_lower:
                results['events_found'].append(pattern)
        
        # Check for major conferences
        for conference in self.conference_patterns['major_conferences']['patterns']:
            if conference in resume_lower:
                results['major_conferences'].append(conference)
        
        # Calculate scores
        if results['speaker_events']:
            results['speaking_score'] = min(len(results['speaker_events']) * 0.3, 1.0)
        
        if results['events_found'] or results['major_conferences']:
            attendance_count = len(results['events_found']) + len(results['major_conferences'])
            results['attendance_score'] = min(attendance_count * 0.15, 0.6)
        
        # Combined conference score (speaking weighted higher)
        results['conference_score'] = min(
            results['speaking_score'] * 0.7 + results['attendance_score'] * 0.3,
            1.0
        )
        
        return results
    
    def score_content_creation(self, resume_text: str) -> Dict[str, Any]:
        """Score technical content creation and community involvement"""
        resume_lower = resume_text.lower()
        
        results = {
            'content_creation_score': 0.0,
            'blog_writing': False,
            'video_content': False,
            'open_source': False,
            'community_involvement': False,
            'content_platforms': [],
            'github_activity': None
        }
        
        content_scores = []
        
        # Check each content type
        for content_type, content_info in self.content_creation.items():
            for pattern in content_info['patterns']:
                if pattern in resume_lower:
                    results[f'{content_type}_activity'] = True
                    results['content_platforms'].append(pattern)
                    content_scores.append(content_info['weight'])
                    
                    # Special handling for GitHub
                    if 'github' in pattern:
                        # Try to extract GitHub stats
                        stats_patterns = [
                            r'(\d+)\+?\s*stars',
                            r'(\d+)\+?\s*followers',
                            r'(\d+)\+?\s*repositories',
                            r'(\d+)\+?\s*contributions'
                        ]
                        github_stats = {}
                        for stat_pattern in stats_patterns:
                            match = re.search(stat_pattern, resume_lower)
                            if match:
                                github_stats[stat_pattern] = int(match.group(1))
                        if github_stats:
                            results['github_activity'] = github_stats
        
        # Calculate overall content creation score
        if content_scores:
            # Average of detected content types with bonus for multiple types
            base_score = sum(content_scores) / len(content_scores)
            variety_bonus = min(len(content_scores) * 0.1, 0.3)
            results['content_creation_score'] = min(base_score + variety_bonus, 1.0)
        
        return results
    
    def calculate_professional_development_score(self, resume_text: str) -> Dict[str, Any]:
        """Calculate comprehensive professional development score"""
        
        # Get all component scores
        cert_results = self.score_certifications(resume_text)
        learning_results = self.score_online_learning(resume_text)
        conference_results = self.score_conference_participation(resume_text)
        content_results = self.score_content_creation(resume_text)
        
        # Calculate weighted overall score
        weights = {
            'certifications': 0.35,
            'online_learning': 0.25,
            'conferences': 0.20,
            'content_creation': 0.20
        }
        
        # Combine main scores
        weighted_score = (
            weights['certifications'] * cert_results['certification_score'] +
            weights['online_learning'] * learning_results['online_learning_score'] +
            weights['conferences'] * conference_results['conference_score'] +
            weights['content_creation'] * content_results['content_creation_score']
        )
        
        # Recency bonus (recent activity is valuable)
        recency_scores = [
            cert_results.get('recent_certification_score', 0),
            learning_results.get('recent_learning_score', 0)
        ]
        recency_bonus = max(recency_scores) * 0.1 if recency_scores else 0
        
        # Calculate final score
        final_score = min(weighted_score + recency_bonus, 1.0)
        
        # Determine professional development level
        pd_level = self._determine_pd_level(final_score, cert_results, learning_results, 
                                           conference_results, content_results)
        
        return {
            'professional_development_score': final_score,
            'professional_development_level': pd_level,
            'component_scores': {
                'certifications': cert_results,
                'online_learning': learning_results,
                'conferences': conference_results,
                'content_creation': content_results
            },
            'weights_used': weights,
            'summary': self._generate_pd_summary(cert_results, learning_results, 
                                                conference_results, content_results)
        }
    
    def _determine_pd_level(self, score: float, cert_results: Dict, learning_results: Dict,
                           conference_results: Dict, content_results: Dict) -> str:
        """Determine professional development level"""
        
        if score >= 0.8:
            return "Exceptional - Continuous learner with strong industry presence"
        elif score >= 0.6:
            return "Strong - Active in professional development"
        elif score >= 0.4:
            return "Moderate - Some professional development activities"
        elif score >= 0.2:
            return "Basic - Limited professional development shown"
        else:
            return "Minimal - Little evidence of continuous learning"
    
    def _generate_pd_summary(self, cert_results: Dict, learning_results: Dict,
                            conference_results: Dict, content_results: Dict) -> Dict[str, Any]:
        """Generate summary of professional development findings"""
        
        summary = {
            'total_certifications': cert_results['certification_count'],
            'certification_categories': list(cert_results['certification_categories'].keys()),
            'recent_certifications': cert_results['recent_certification_score'] > 0.7,
            'learning_platforms_used': len(learning_results['platforms_found']),
            'estimated_courses_completed': learning_results['course_count_estimate'],
            'conference_speaker': len(conference_results['speaker_events']) > 0,
            'conferences_attended': len(conference_results['events_found']),
            'content_creator': content_results['content_creation_score'] > 0.5,
            'content_types': [k.replace('_activity', '') for k, v in content_results.items() 
                            if k.endswith('_activity') and v],
            'continuous_learner': (
                cert_results['recent_certification_score'] > 0.7 or 
                learning_results['recent_learning_score'] > 0.7
            )
        }
        
        # Key highlights
        highlights = []
        if summary['total_certifications'] >= 3:
            highlights.append(f"Has {summary['total_certifications']} professional certifications")
        if summary['conference_speaker']:
            highlights.append("Conference speaker")
        if summary['content_creator']:
            highlights.append("Active content creator")
        if summary['continuous_learner']:
            highlights.append("Recent learning activities (within 2 years)")
        if 'cloud' in summary['certification_categories']:
            highlights.append("Cloud certified professional")
        
        summary['key_highlights'] = highlights
        
        return summary


class UpdateAwareResumeFilter:
    """Resume filter that considers updated job requirements and professional development"""
    
    def __init__(self):
        self.skill_variations = self._build_skill_variations()
        # Add the professional development scorer
        self.pd_scorer = ProfessionalDevelopmentScorer()
    
    def _build_skill_variations(self) -> Dict[str, List[str]]:
        """Build comprehensive skill variations dictionary"""
        return {
            # Programming Languages
            "python": ["python", "py", "python3", "python2", "python 3", "python 2"],
            "javascript": ["javascript", "js", "node.js", "nodejs", "node", "ecmascript", "es6", "es5"],
            "java": ["java", "jvm", "j2ee", "java8", "java11", "java17"],
            "c++": ["c++", "cpp", "cplusplus", "c plus plus"],
            "c#": ["c#", "csharp", "c sharp", ".net", "dotnet"],
            
            # Web Technologies
            "html": ["html", "html5", "html 5"],
            "css": ["css", "css3", "css 3", "styles", "styling"],
            "html/css": ["html/css", "html css", "html, css", "html and css", "html & css"],
            
            # Databases
            "sql": ["sql", "structured query language", "tsql", "t-sql", "plsql", "pl/sql"],
            "mongodb": ["mongodb", "mongo", "mongod", "nosql mongodb"],
            "redis": ["redis", "redis cache", "redis db", "redis database"],
            "postgresql": ["postgresql", "postgres", "pgsql", "postgre"],
            "mysql": ["mysql", "my sql", "mariadb"],
            
            # Frameworks
            "react": ["react", "reactjs", "react.js", "react js", "react native"],
            "angular": ["angular", "angularjs", "angular.js", "angular js"],
            "django": ["django", "django rest", "drf", "django framework"],
            "spring": ["spring", "spring boot", "springboot", "spring framework"],
            "flask": ["flask", "flask api", "flask framework"],
            
            # Cloud Platforms
            "aws": ["aws", "amazon web services", "ec2", "s3", "lambda", "amazon aws"],
            "gcp": ["gcp", "google cloud", "google cloud platform", "gcloud"],
            "azure": ["azure", "microsoft azure", "ms azure", "windows azure"],
            "cloud platforms": ["cloud platforms", "cloud services", "cloud computing", "cloud infrastructure"],
            
            # Big Data
            "spark": ["spark", "apache spark", "pyspark", "spark sql"],
            "hadoop": ["hadoop", "hdfs", "mapreduce", "apache hadoop"],
            "kafka": ["kafka", "apache kafka", "kafka streams"],
            
            # Machine Learning
            "machine learning": ["machine learning", "ml", "scikit-learn", "sklearn", "ml models"],
            "deep learning": ["deep learning", "dl", "neural networks", "nn", "dnn"],
            "tensorflow": ["tensorflow", "tf", "tf2", "tensorflow 2"],
            "pytorch": ["pytorch", "torch", "py torch"],
            
            # Others
            "docker": ["docker", "containers", "containerization", "dockerfile"],
            "kubernetes": ["kubernetes", "k8s", "kubectl", "k8", "container orchestration"],
            "graphql": ["graphql", "graph ql", "apollo", "graphql api"],
            "rest": ["rest", "restful", "rest api", "restful api", "rest services"],
            "rest apis": ["rest apis", "restful apis", "rest api", "restful api", "api development"],
            "git": ["git", "github", "gitlab", "bitbucket", "version control", "vcs"],
            "ci/cd": ["ci/cd", "cicd", "continuous integration", "continuous deployment", "jenkins", "travis", "circle ci"],
            "agile": ["agile", "scrum", "kanban", "sprint", "agile methodology"],
            
            # Data Engineering specific
            "etl": ["etl", "elt", "extract transform load", "data pipeline", "data pipelines"],
            "data warehouse": ["data warehouse", "data warehousing", "dwh", "datawarehouse"],
            "apache spark": ["apache spark", "spark", "pyspark", "spark sql", "spark streaming"],
            
            # Database categories
            "sql/nosql databases": ["sql/nosql", "sql nosql", "sql and nosql", "relational and non-relational", 
                                   "sql", "nosql", "mysql", "postgresql", "mongodb", "cassandra", "redis",
                                   "database", "databases", "rdbms", "nosql databases"],
        }
    
    def calculate_skill_match_score(self, resume_text: str, required_skills: List[str]) -> tuple[float, List[str], Dict[str, List[str]]]:
        """Calculate skill matching score with variations"""
        resume_lower = resume_text.lower()
        matched_skills = []
        detailed_matches = {}
        
        for skill in required_skills:
            skill_lower = skill.lower().strip()
            skill_matched = False
            
            if skill_lower in resume_lower:
                matched_skills.append(skill)
                detailed_matches[skill] = [skill_lower]
                skill_matched = True
                continue
            
            skill_key = None
            for key in self.skill_variations:
                if skill_lower in self.skill_variations[key] or key in skill_lower:
                    skill_key = key
                    break
            
            if skill_key and skill_key in self.skill_variations:
                variations_found = []
                for variation in self.skill_variations[skill_key]:
                    if variation in resume_lower:
                        variations_found.append(variation)
                        skill_matched = True
                
                if variations_found:
                    matched_skills.append(skill)
                    detailed_matches[skill] = variations_found
            
            if not skill_matched and ' ' in skill:
                parts = skill.split()
                if all(part.lower() in resume_lower for part in parts):
                    matched_skills.append(skill)
                    detailed_matches[skill] = [skill_lower]
        
        score = len(matched_skills) / len(required_skills) if required_skills else 0
        return score, matched_skills, detailed_matches
    
    def parse_experience_range(self, experience_str: str) -> tuple[int, int]:
        """Parse experience range like '5-8 years' to (5, 8)"""
        numbers = re.findall(r'\d+', experience_str)
        
        if len(numbers) >= 2:
            return int(numbers[0]), int(numbers[1])
        elif len(numbers) == 1:
            if '+' in experience_str:
                return int(numbers[0]), int(numbers[0]) + 5
            else:
                return int(numbers[0]), int(numbers[0])
        else:
            return 0, 100
    
    def calculate_experience_match(self, resume_text: str, required_experience: str) -> tuple[float, int]:
        """Calculate experience matching score"""
        min_req, max_req = self.parse_experience_range(required_experience)
        
        # Enhanced patterns to better detect experience
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:professional\s*)?experience',
            r'experience\s*[:–-]\s*(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?\s*in\s*(?:software|data|engineering|development)',
            r'total\s*experience\s*[:–-]\s*(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?\s*exp',
            r'(\d{4})\s*[-–]\s*(?:present|current|now|(\d{4}))',
        ]
        
        # Additional patterns for date ranges
        date_patterns = [
            # From Month Year - Present/Current format
            r'from\s+(?:january|february|march|april|may|june|july|august|september|october|november|december),?\s*(\d{4})\s*[-–]\s*(?:present|current|now)',
            # Month Year - Month Year format
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december),?\s*(\d{4})\s*[-–]\s*(?:january|february|march|april|may|june|july|august|september|october|november|december),?\s*(\d{4})',
            # Year to Year format
            r'(\d{4})\s*(?:to|-|–)\s*(\d{4})',
            # Since Year format
            r'since\s+(?:january|february|march|april|may|june|july|august|september|october|november|december),?\s*(\d{4})',
        ]
        
        # New pattern specifically for "August, 2023 - Present" format
        month_year_patterns = [
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december),?\s*(\d{4})\s*[-–]\s*(?:present|current|now)',
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*,?\s*(\d{4})\s*[-–]\s*(?:present|current|now)',
        ]
        
        years_found = []
        experience_periods = []
        
        # Check if we're in an education section (to avoid counting graduation years)
        education_keywords = ['education', 'academic', 'degree', 'bachelor', 'master', 'phd', 'university', 'college', 'school']
        
        # First try to find explicit year mentions (but not in education sections)
        for pattern in patterns:
            matches = re.findall(pattern, resume_text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    if match[0].isdigit() and len(match[0]) == 4:
                        start_year = int(match[0])
                        if match[1] and match[1].isdigit():
                            end_year = int(match[1])
                        else:
                            end_year = datetime.now().year
                        
                        # Check if this year range is likely education-related
                        match_context = resume_text.lower()[max(0, resume_text.lower().find(match[0])-100):resume_text.lower().find(match[0])+100]
                        if not any(edu_keyword in match_context for edu_keyword in education_keywords):
                            if 1990 < start_year <= datetime.now().year:
                                years_found.append(end_year - start_year)
                else:
                    if match.isdigit():
                        years_found.append(int(match))
        
        # Try month/year patterns specifically in experience/work sections
        experience_keywords = ['experience', 'work', 'employed', 'position', 'role', 'job', 'company', 'engineer at', 'developer at']
        
        for pattern in month_year_patterns:
            for match in re.finditer(pattern, resume_text.lower()):
                match_text = match.group(1) if match.groups() else match.group(0)
                if match_text.isdigit():
                    start_year = int(match_text)
                    
                    # Check if this is in an experience context
                    match_context = resume_text.lower()[max(0, match.start()-200):match.end()+50]
                    if any(exp_keyword in match_context for exp_keyword in experience_keywords):
                        if 1990 < start_year <= datetime.now().year:
                            # Calculate fractional years for recent experience
                            current_year = datetime.now().year
                            current_month = datetime.now().month
                            
                            # Estimate based on the month mentioned
                            month_str = resume_text.lower()[max(0, match.start()-20):match.start()].strip()
                            
                            # Map months to numbers
                            month_map = {
                                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                                'september': 9, 'october': 10, 'november': 11, 'december': 12
                            }
                            
                            start_month = 1  # Default to January
                            for month_name, month_num in month_map.items():
                                if month_name in month_str:
                                    start_month = month_num
                                    break
                            
                            # Calculate experience more accurately
                            if start_year == current_year:
                                years = (current_month - start_month) / 12.0
                            elif start_year == current_year - 1:
                                years = 1 + ((current_month - start_month) / 12.0)
                            else:
                                years = current_year - start_year + ((current_month - start_month) / 12.0)
                            
                            experience_periods.append(max(0.5, years))  # At least 0.5 years
        
        # Try date patterns to calculate experience
        for pattern in date_patterns:
            matches = re.findall(pattern, resume_text.lower())
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) >= 1:
                        start_year = int(match[0])
                        if len(match) > 1 and match[1] and match[1].isdigit():
                            end_year = int(match[1])
                        else:
                            end_year = datetime.now().year
                        
                        # Check context
                        match_context = resume_text.lower()[max(0, resume_text.lower().find(str(start_year))-100):resume_text.lower().find(str(start_year))+100]
                        if any(exp_keyword in match_context for exp_keyword in experience_keywords) and \
                           not any(edu_keyword in match_context for edu_keyword in education_keywords):
                            if 1990 < start_year <= datetime.now().year and end_year - start_year < 10:
                                experience_periods.append(end_year - start_year)
                elif match and match.isdigit():
                    start_year = int(match)
                    if 1990 < start_year <= datetime.now().year:
                        experience_periods.append(datetime.now().year - start_year)
        
        # Combine all found years
        all_years = years_found + experience_periods
        
        if all_years:
            # Filter out unrealistic values (likely education years)
            realistic_years = [y for y in all_years if 0 < y < 15]
            
            if realistic_years:
                # Take the maximum reasonable experience
                candidate_years = max(realistic_years)
                # Round fractional years
                if candidate_years < 1:
                    candidate_years = 1
                else:
                    candidate_years = int(round(candidate_years))
            else:
                candidate_years = int(round(max(all_years)))
            
            if min_req <= candidate_years <= max_req:
                return 1.0, candidate_years
            elif candidate_years > max_req:
                return 0.9, candidate_years
            elif candidate_years >= min_req - 1:
                return 0.8, candidate_years
            else:
                return candidate_years / min_req if min_req > 0 else 0, candidate_years
        
        return 0.0, 0
    
    def score_resume(self, resume_text: str, job_ticket: EnhancedJobTicket) -> Dict[str, Any]:
        """Enhanced score_resume method with professional development"""
        
        # Your existing scoring logic
        skill_score, matched_skills, detailed_matches = self.calculate_skill_match_score(
            resume_text, job_ticket.tech_stack
        )
        
        exp_score, detected_years = self.calculate_experience_match(
            resume_text, job_ticket.experience_required
        )
        
        location_score = 0.0
        if job_ticket.location.lower() in resume_text.lower():
            location_score = 1.0
        elif "remote" in job_ticket.location.lower() or "remote" in resume_text.lower():
            location_score = 0.8
        
        # Add professional development scoring
        pd_results = self.pd_scorer.calculate_professional_development_score(resume_text)
        
        # Updated weights to include professional development
        weights = {
            'skills': 0.40,           # Reduced from 0.50
            'experience': 0.30,       # Reduced from 0.35
            'location': 0.10,         # Reduced from 0.15
            'professional_dev': 0.20  # New weight for PD
        }
        
        # Calculate final score with professional development
        final_score = (
            weights['skills'] * skill_score +
            weights['experience'] * exp_score +
            weights['location'] * location_score +
            weights['professional_dev'] * pd_results['professional_development_score']
        )
        
        return {
            'final_score': final_score,
            'skill_score': skill_score,
            'experience_score': exp_score,
            'location_score': location_score,
            'professional_development_score': pd_results['professional_development_score'],
            'matched_skills': matched_skills,
            'detailed_skill_matches': detailed_matches,
            'detected_experience_years': detected_years,
            'professional_development': pd_results,
            'scoring_weights': weights,
            'job_requirements': {
                'position': job_ticket.position,
                'required_skills': job_ticket.tech_stack,
                'required_experience': job_ticket.experience_required,
                'location': job_ticket.location
            }
        }


class UpdateAwareBasicFilter:
    """Enhanced basic filter with comprehensive scoring and duplicate detection"""
    
    def __init__(self):
        self.resume_filter = UpdateAwareResumeFilter()
        self.duplicate_detector = DuplicateCandidateDetector()
        self.duplicate_handler = DuplicateHandlingStrategy()
        
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            os.system("python -m spacy download en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")
        
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2)
        )
    
    def score_resume_comprehensive(self, resume_text: str, resume_path: Path, job_ticket: EnhancedJobTicket) -> Dict:
        """Comprehensive scoring using multiple methods"""
        base_scores = self.resume_filter.score_resume(resume_text, job_ticket)
        
        similarity_score = 0.0
        if job_ticket.description:
            try:
                tfidf_matrix = self.vectorizer.fit_transform([job_ticket.description, resume_text])
                similarity_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            except:
                similarity_score = 0.0
        
        additional_features = self._extract_additional_features(resume_text)
        
        result = {
            "file_path": str(resume_path),
            "filename": resume_path.name,
            "final_score": base_scores['final_score'],
            "skill_score": base_scores['skill_score'],
            "experience_score": base_scores['experience_score'],
            "location_score": base_scores['location_score'],
            "professional_development_score": base_scores['professional_development_score'],
            "similarity_score": similarity_score,
            "matched_skills": base_scores['matched_skills'],
            "detailed_skill_matches": base_scores['detailed_skill_matches'],
            "detected_experience_years": base_scores['detected_experience_years'],
            "professional_development": base_scores['professional_development'],
            "additional_features": additional_features,
            "scoring_weights": base_scores['scoring_weights'],
            "job_requirements_used": base_scores['job_requirements']
        }
        
        return result
    
    def _extract_additional_features(self, resume_text: str) -> Dict:
        """Extract additional features from resume"""
        features = {}
        
        education_keywords = {
            'phd': 4, 'doctorate': 4,
            'master': 3, 'mba': 3, 'ms': 3, 'mtech': 3,
            'bachelor': 2, 'btech': 2, 'bs': 2, 'be': 2,
            'diploma': 1
        }
        
        resume_lower = resume_text.lower()
        education_score = 0
        for keyword, score in education_keywords.items():
            if keyword in resume_lower:
                education_score = max(education_score, score)
        
        features['education_level'] = education_score
        
        cert_keywords = ['certified', 'certification', 'certificate', 'aws certified', 'google certified', 'microsoft certified']
        features['has_certifications'] = any(cert in resume_lower for cert in cert_keywords)
        
        leadership_keywords = ['lead', 'manager', 'head', 'director', 'principal', 'senior', 'architect']
        features['leadership_experience'] = sum(1 for keyword in leadership_keywords if keyword in resume_lower)
        
        return features


class UpdatedResumeFilteringSystem:
    """Complete resume filtering system with update support and duplicate detection"""
    
    def __init__(self, ticket_folder: str):
        self.ticket_folder = Path(ticket_folder)
        self.job_ticket = EnhancedJobTicket(ticket_folder)
        self.basic_filter = UpdateAwareBasicFilter()
        
        self.output_folder = self.ticket_folder / "filtering_results"
        self.output_folder.mkdir(exist_ok=True)
        
        self._create_agents()
    
    def _create_agents(self):
        """Create AutoGen agents with latest job requirements"""
        latest_skills = ', '.join(self.job_ticket.tech_stack)
        latest_experience = self.job_ticket.experience_required
        latest_salary = self.job_ticket.salary_range
        
        llm_config = {
            "config_list": config_list,
            "temperature": 0.2,
            "timeout": 60,
            "cache_seed": 42,
        }
        
        llm_config_basic = {
            "config_list": config_list_basic,
            "temperature": 0.1,
            "timeout": 30,
            "cache_seed": 42,
        }
        
        self.basic_filter_agent = autogen.AssistantAgent(
            name="basic_filter_agent",
            llm_config=llm_config_basic,
            system_message=f"""You are a resume screening assistant for: {self.job_ticket.position}
            
            JOB REQUIREMENTS:
            - Experience: {latest_experience}
            - Required Skills: {latest_skills}
            - Location: {self.job_ticket.location}
            - Salary: {latest_salary}
            - Deadline: {self.job_ticket.deadline}
            
            Review resume scores and validate selections based on requirements.
            Flag any candidates who don't meet the criteria.
            Also consider professional development as a positive indicator.
            Pay attention to duplicate candidates and recommend keeping the best submission.
            """
        )
        
        self.advanced_filter_agent = autogen.AssistantAgent(
            name="advanced_filter_agent",
            llm_config=llm_config,
            system_message=f"""You are an expert technical recruiter evaluating for: {self.job_ticket.position}
            
            REQUIREMENTS:
            - Experience Range: {latest_experience}
            - Must-Have Skills: {latest_skills}
            - Location: {self.job_ticket.location}
            - Salary Budget: {latest_salary}
            
            Select the BEST 5 candidates who meet the requirements.
            Consider the skill requirements especially: {latest_skills}
            Also value professional development activities like certifications, 
            continuous learning, conference participation, and content creation 
            as indicators of candidate quality and commitment to growth.
            
            Note: Some candidates may have applied multiple times. Consider only their best submission.
            
            Rank 1-5 based on fit with requirements.
            """
        )
        
        self.qa_agent = autogen.AssistantAgent(
            name="qa_agent",
            llm_config=llm_config,
            system_message=f"""Quality assurance specialist reviewing selections.
            
            Ensure all selections meet the requirements:
            - Skills: {latest_skills}
            - Experience: {latest_experience}
            - Salary: {latest_salary}
            
            Verify requirements were properly evaluated.
            Check that professional development was considered.
            Ensure duplicate candidates were properly handled.
            """
        )
        
        self.user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,
            code_execution_config={
                "work_dir": str(self.output_folder),
                "use_docker": False,
            }
        )
    
    def filter_resumes(self) -> Dict:
        """Main filtering method with update awareness and duplicate detection"""
        print(f"\n{'='*70}")
        print(f"🚀 RESUME FILTERING SYSTEM")
        print(f"{'='*70}")
        print(f"Job Ticket: {self.job_ticket.ticket_id}")
        print(f"Position: {self.job_ticket.position}")
        print(f"\n📋 JOB REQUIREMENTS:")
        print(f"  • Experience: {self.job_ticket.experience_required}")
        print(f"  • Skills: {', '.join(self.job_ticket.tech_stack)}")
        print(f"  • Location: {self.job_ticket.location}")
        print(f"  • Salary: {self.job_ticket.salary_range}")
        print(f"  • Deadline: {self.job_ticket.deadline}")
        print(f"{'='*70}\n")
        
        resumes = self.job_ticket.get_resumes()
        print(f"📄 Found {len(resumes)} resumes to process")
        
        if not resumes:
            return {
                "error": "No resumes found in the ticket folder",
                "ticket_id": self.job_ticket.ticket_id
            }
        
        print("\n🔍 Stage 1: Basic AI Filtering with Duplicate Detection...")
        initial_results = self._basic_filtering_with_duplicates(resumes)
        
        with open(self.output_folder / "stage1_results.json", 'w') as f:
            json.dump(initial_results, f, indent=2, default=str)
        
        print("\n🧠 Stage 2: Advanced LLM Analysis...")
        final_results = self._advanced_filtering(initial_results)
        
        with open(self.output_folder / "stage2_results.json", 'w') as f:
            json.dump(final_results, f, indent=2, default=str)
        
        print("\n✅ Stage 3: Quality Assurance Review...")
        qa_results = self._quality_assurance(initial_results, final_results)
        
        final_output = {
            "ticket_id": self.job_ticket.ticket_id,
            "position": self.job_ticket.position,
            "timestamp": datetime.now().isoformat(),
            "job_status": self.job_ticket.job_details.get('status', 'unknown'),
            "requirements_last_updated": self.job_ticket.job_details.get('last_updated', ''),
            "latest_requirements": {
                "experience": self.job_ticket.experience_required,
                "tech_stack": self.job_ticket.tech_stack,
                "location": self.job_ticket.location,
                "salary": self.job_ticket.salary_range,
                "deadline": self.job_ticket.deadline
            },
            "summary": {
                "total_resumes": len(resumes),
                "unique_candidates": initial_results.get('unique_candidates', len(resumes)),
                "duplicate_groups_found": initial_results.get('duplicate_groups_count', 0),
                "stage1_selected": len(initial_results["top_10"]),
                "final_selected": len(final_results.get("top_5_candidates", [])),
            },
            "duplicate_detection": initial_results.get('duplicate_summary', {}),
            "stage1_results": initial_results,
            "stage2_results": final_results,
            "qa_review": qa_results,
            "final_top_5": final_results.get("top_5_candidates", []),
        }
        
        output_file = self.output_folder / f"final_results_{self.job_ticket.ticket_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(final_output, f, indent=2, default=str)
        
        self._create_enhanced_summary_report(final_output)
        
        print(f"\n✅ Filtering complete! Results saved to: {output_file}")
        
        return final_output
    
    def _basic_filtering_with_duplicates(self, resumes: List[Path]) -> Dict:
        """Stage 1 with duplicate detection and handling"""
        
        # First pass: detect duplicates
        print("\n🔍 Detecting duplicate candidates...")
        
        duplicate_map = {}  # Map of filename to candidate_id
        
        for resume_path in resumes:
            resume_text = ResumeExtractor.extract_text(resume_path)
            if not resume_text:
                continue
            
            candidate_id, duplicates = self.basic_filter.duplicate_detector.add_candidate(
                resume_text, resume_path.name
            )
            
            duplicate_map[resume_path.name] = {
                'candidate_id': candidate_id,
                'duplicates': duplicates
            }
            
            if duplicates:
                print(f"  ⚠️ {resume_path.name} has {len(duplicates)} duplicate(s):")
                for dup in duplicates:
                    print(f"     - {dup['filename']} (confidence: {dup['confidence']:.1%}, reason: {dup['reason']})")
        
        # Get duplicate groups
        dup_groups = self.basic_filter.duplicate_detector.get_duplicate_groups()
        
        # Second pass: score resumes
        print("\n📊 Scoring resumes...")
        scored_resumes = []
        processed_candidates = set()  # Track processed candidate IDs
        
        for i, resume_path in enumerate(resumes):
            print(f"  Processing {i+1}/{len(resumes)}: {resume_path.name}")
            
            resume_text = ResumeExtractor.extract_text(resume_path)
            if not resume_text:
                print(f"    ⚠️ Failed to extract text from {resume_path.name}")
                continue
            
            # Check if this candidate was already processed as part of a duplicate group
            candidate_info = duplicate_map.get(resume_path.name, {})
            candidate_id = candidate_info.get('candidate_id')
            
            # Score the resume
            score_result = self.basic_filter.score_resume_comprehensive(
                resume_text, 
                resume_path,
                self.job_ticket
            )
            
            score_result['candidate_id'] = candidate_id
            
            # Add duplicate information
            if candidate_info.get('duplicates'):
                score_result['has_duplicates'] = True
                score_result['duplicate_count'] = len(candidate_info['duplicates'])
                score_result['duplicates'] = candidate_info['duplicates']
            else:
                score_result['has_duplicates'] = False
            
            scored_resumes.append(score_result)
        
        # Handle duplicates - merge scores for duplicate groups
        final_scored_resumes = self._merge_duplicate_scores(scored_resumes, dup_groups)
        
        # Sort by score
        final_scored_resumes.sort(key=lambda x: x["final_score"], reverse=True)
        top_10 = final_scored_resumes[:10]
        
        # Print summary
        print("\n📊 Top Candidates (after duplicate handling):")
        for i, candidate in enumerate(top_10[:min(len(top_10), 5)]):
            print(f"  {i+1}. {candidate['filename']} - Score: {candidate['final_score']:.2%}")
            print(f"      Skills: {len(candidate['matched_skills'])}/{len(self.job_ticket.tech_stack)} matched")
            print(f"      Experience: {candidate['detected_experience_years']} years")
            print(f"      Prof. Development: {candidate['professional_development_score']:.2%}")
            if candidate.get('has_duplicates'):
                print(f"      ⚠️ Best of {candidate.get('duplicate_count', 1) + 1} submissions")
        
        # Prepare duplicate summary
        duplicate_summary = {
            "total_resumes_submitted": len(resumes),
            "unique_candidates": len(final_scored_resumes),
            "duplicate_groups_found": len(dup_groups),
            "duplicate_groups": [
                {
                    "group_size": len(group),
                    "filenames": [item['filename'] for item in group]
                }
                for group in dup_groups
            ]
        }
        
        print(f"\n📊 Duplicate Detection Summary:")
        print(f"  Total resumes submitted: {duplicate_summary['total_resumes_submitted']}")
        print(f"  Unique candidates: {duplicate_summary['unique_candidates']}")
        print(f"  Duplicate groups found: {duplicate_summary['duplicate_groups_found']}")
        
        # Prepare agent review data
        review_summary = self._prepare_agent_review_data(top_10)
        
        # Get agent review
        self.user_proxy.initiate_chat(
            self.basic_filter_agent,
            message=f"""Review these candidates:

{json.dumps(review_summary, indent=2)}

Note: Some candidates had multiple submissions. The scores shown are their best performance.

Confirm they meet the requirements, especially skills: {', '.join(self.job_ticket.tech_stack)}
""",
            max_turns=1
        )
        
        return {
            "all_resumes": final_scored_resumes,
            "top_10": top_10,
            "agent_review": self.basic_filter_agent.last_message()["content"],
            "scoring_criteria": {
                "skills_required": self.job_ticket.tech_stack,
                "experience_range": self.job_ticket.experience_required,
                "location": self.job_ticket.location
            },
            "duplicate_summary": duplicate_summary,
            "unique_candidates": len(final_scored_resumes),
            "duplicate_groups_count": len(dup_groups)
        }
    
    def _merge_duplicate_scores(self, scored_resumes: List[Dict], dup_groups: List[List[Dict]]) -> List[Dict]:
        """Merge scores for duplicate candidates"""
        
        # Create a map of candidate_id to resumes
        id_to_resumes = defaultdict(list)
        for resume in scored_resumes:
            if resume.get('candidate_id'):
                id_to_resumes[resume['candidate_id']].append(resume)
        
        # Process duplicate groups
        final_results = []
        processed_ids = set()
        
        # First, handle duplicate groups
        for group in dup_groups:
            group_candidate_ids = [item['candidate_id'] for item in group]
            group_resumes = []
            
            for cid in group_candidate_ids:
                if cid in id_to_resumes:
                    group_resumes.extend(id_to_resumes[cid])
            
            if group_resumes:
                # Merge scores from duplicates
                merged_candidate = self.basic_filter.duplicate_handler.merge_scores(group_resumes)
                final_results.append(merged_candidate)
                
                # Mark all in group as processed
                for cid in group_candidate_ids:
                    processed_ids.add(cid)
        
        # Then add non-duplicate candidates
        for resume in scored_resumes:
            cid = resume.get('candidate_id')
            if cid and cid not in processed_ids:
                final_results.append(resume)
                processed_ids.add(cid)
            elif not cid:
                # Resume without candidate_id (failed duplicate detection)
                final_results.append(resume)
        
        return final_results
    
    def _prepare_agent_review_data(self, top_10: List[Dict]) -> List[Dict]:
        """Prepare summary data for agent review with professional development and duplicate info"""
        summary = []
        
        for i, candidate in enumerate(top_10[:min(len(top_10), 5)]):
            candidate_summary = {
                "rank": i + 1,
                "filename": candidate["filename"],
                "overall_score": f"{candidate['final_score']:.1%}",
                "skill_match": f"{candidate['skill_score']:.1%} ({len(candidate['matched_skills'])}/{len(self.job_ticket.tech_stack)})",
                "matched_skills": candidate["matched_skills"],
                "missing_skills": [s for s in self.job_ticket.tech_stack if s not in candidate["matched_skills"]],
                "experience": f"{candidate['detected_experience_years']} years (Score: {candidate['experience_score']:.1%})",
                "location_match": "Yes" if candidate['location_score'] > 0 else "No"
            }
            
            # Add professional development summary
            if 'professional_development' in candidate:
                pd_data = candidate['professional_development']
                pd_summary = pd_data['summary']
                
                candidate_summary["professional_development"] = {
                    "score": f"{pd_data['professional_development_score']:.1%}",
                    "level": pd_data['professional_development_level'],
                    "certifications": pd_summary['total_certifications'],
                    "continuous_learner": pd_summary['continuous_learner'],
                    "highlights": pd_summary.get('key_highlights', [])[:2]  # Top 2 highlights
                }
            
            # Add duplicate information
            if candidate.get('has_duplicates'):
                candidate_summary["duplicate_info"] = {
                    "is_duplicate": True,
                    "submissions": candidate.get('duplicate_count', 1) + 1,
                    "note": "Best score from multiple submissions"
                }
            
            summary.append(candidate_summary)
        
        return summary
    
    def _advanced_filtering(self, initial_results: Dict) -> Dict:
        """Stage 2: Advanced filtering with detailed analysis"""
        top_10 = initial_results["top_10"]
        
        # For small candidate pools
        candidates_to_analyze = min(len(top_10), 5)
        
        detailed_candidates = []
        for i, candidate in enumerate(top_10[:candidates_to_analyze]):
            resume_text = ResumeExtractor.extract_text(Path(candidate["file_path"]))
            
            max_chars = 2000
            if len(resume_text) > max_chars:
                resume_text = resume_text[:max_chars] + "\n[... truncated]"
            
            detailed_candidate = {
                "rank": i + 1,
                "filename": candidate["filename"],
                "scores": {
                    "overall": f"{candidate['final_score']:.1%}",
                    "skills": f"{candidate['skill_score']:.1%}",
                    "experience": f"{candidate['experience_score']:.1%}",
                    "professional_development": f"{candidate['professional_development_score']:.1%}"
                },
                "matched_skills": candidate["matched_skills"],
                "missing_skills": [s for s in self.job_ticket.tech_stack if s not in candidate["matched_skills"]],
                "experience_years": candidate["detected_experience_years"],
                "pd_highlights": candidate['professional_development']['summary'].get('key_highlights', []),
                "resume_preview": resume_text
            }
            
            # Add duplicate info if present
            if candidate.get('has_duplicates'):
                detailed_candidate["duplicate_status"] = f"Best of {candidate.get('duplicate_count', 1) + 1} submissions"
            
            detailed_candidates.append(detailed_candidate)
        
        analysis_prompt = f"""Analyze these candidates for {self.job_ticket.position}.

REQUIREMENTS:
- Skills: {', '.join(self.job_ticket.tech_stack)}
- Experience: {self.job_ticket.experience_required}
- Location: {self.job_ticket.location}

CANDIDATES:
{json.dumps(detailed_candidates, indent=2)}

Select the TOP candidates based on fit with requirements.
Consider professional development as a positive factor.
Note: Some candidates may have submitted multiple applications - we're showing their best scores.
"""
        
        self.user_proxy.initiate_chat(
            self.advanced_filter_agent,
            message=analysis_prompt,
            max_turns=1
        )
        
        top_5_candidates = []
        for i in range(min(candidates_to_analyze, len(top_10))):
            candidate = top_10[i].copy()
            candidate["final_rank"] = i + 1
            candidate["selection_reason"] = f"Strong match for requirements"
            top_5_candidates.append(candidate)
        
        return {
            "top_5_candidates": top_5_candidates,
            "detailed_analysis": self.advanced_filter_agent.last_message()["content"],
            "selection_criteria": "Based on job requirements, professional development, and best submission per candidate",
            "requirements_version": self.job_ticket.job_details.get('last_updated', 'Unknown')
        }
    
    def _quality_assurance(self, initial_results: Dict, final_results: Dict) -> Dict:
        """QA review ensuring requirements were used properly and duplicates handled"""
        qa_prompt = f"""Review the filtering process:

JOB: {self.job_ticket.position}

REQUIREMENTS:
- Skills: {', '.join(self.job_ticket.tech_stack)}
- Experience: {self.job_ticket.experience_required}
- Location: {self.job_ticket.location}
- Salary: {self.job_ticket.salary_range}

PROCESS SUMMARY:
- {len(initial_results['all_resumes'])} resumes processed
- {initial_results.get('unique_candidates', len(initial_results['all_resumes']))} unique candidates identified
- {initial_results.get('duplicate_groups_count', 0)} duplicate groups found
- Top candidates selected
- Final candidates chosen
- Professional development considered

Verify:
1. Were skill requirements properly evaluated?
2. Does experience range match requirements?
3. Was professional development considered appropriately?
4. Were duplicate candidates properly handled (best score selected)?
5. Any concerns about the process?
6. Recommendations for improvement?
"""
        
        self.user_proxy.initiate_chat(
            self.qa_agent,
            message=qa_prompt,
            max_turns=1
        )
        
        return {
            "qa_assessment": self.qa_agent.last_message()["content"],
            "requirements_verified": True,
            "duplicates_handled": True,
            "qa_timestamp": datetime.now().isoformat()
        }
    
    def _create_enhanced_summary_report(self, results: Dict):
        """Create detailed summary report with professional development insights and duplicate info"""
        report_path = self.output_folder / f"summary_report_{self.job_ticket.ticket_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_path, 'w') as f:
            f.write(f"RESUME FILTERING SUMMARY REPORT\n")
            f.write(f"{'='*70}\n\n")
            f.write(f"Job Ticket ID: {results['ticket_id']}\n")
            f.write(f"Position: {results['position']}\n")
            f.write(f"Report Generated: {results['timestamp']}\n")
            
            f.write(f"\n{'='*70}\n")
            f.write(f"JOB REQUIREMENTS:\n")
            f.write(f"{'='*70}\n")
            f.write(f"Experience: {results['latest_requirements']['experience']}\n")
            f.write(f"Skills: {', '.join(results['latest_requirements']['tech_stack'])}\n")
            f.write(f"Location: {results['latest_requirements']['location']}\n")
            f.write(f"Salary: {results['latest_requirements']['salary']}\n")
            f.write(f"Deadline: {results['latest_requirements']['deadline']}\n")
            
            f.write(f"\n{'='*70}\n")
            f.write(f"FILTERING SUMMARY:\n")
            f.write(f"{'='*70}\n")
            f.write(f"Total Resumes Submitted: {results['summary']['total_resumes']}\n")
            f.write(f"Unique Candidates: {results['summary']['unique_candidates']}\n")
            f.write(f"Duplicate Groups Found: {results['summary']['duplicate_groups_found']}\n")
            f.write(f"Final Selected: {results['summary']['final_selected']}\n")
            
            # Duplicate detection details
            if results.get('duplicate_detection') and results['duplicate_detection'].get('duplicate_groups'):
                f.write(f"\n{'='*70}\n")
                f.write(f"DUPLICATE CANDIDATES DETECTED:\n")
                f.write(f"{'='*70}\n")
                for i, group in enumerate(results['duplicate_detection']['duplicate_groups'], 1):
                    f.write(f"\nGroup {i} ({group['group_size']} submissions):\n")
                    for filename in group['filenames']:
                        f.write(f"  - {filename}\n")
            
            f.write(f"\n{'='*70}\n")
            f.write(f"TOP CANDIDATES (RANKED):\n")
            f.write(f"{'='*70}\n\n")
            
            for i, candidate in enumerate(results['final_top_5']):
                f.write(f"{i+1}. {candidate['filename']}\n")
                f.write(f"   Overall Score: {candidate['final_score']:.1%}\n")
                f.write(f"   Skill Match: {candidate['skill_score']:.1%} ({len(candidate['matched_skills'])}/{len(results['latest_requirements']['tech_stack'])} skills)\n")
                f.write(f"   Matched Skills: {', '.join(candidate['matched_skills'])}\n")
                f.write(f"   Experience: {candidate['detected_experience_years']} years (Score: {candidate['experience_score']:.1%})\n")
                f.write(f"   Location Match: {'Yes' if candidate['location_score'] > 0 else 'No'}\n")
                
                # Add duplicate information
                if candidate.get('has_duplicates'):
                    f.write(f"   ⚠️ DUPLICATE: Best of {candidate.get('duplicate_count', 1) + 1} submissions\n")
                    if candidate.get('duplicate_info') and candidate['duplicate_info'].get('filenames'):
                        f.write(f"      Other submissions: {', '.join(candidate['duplicate_info']['filenames'][1:])}\n")
                
                # Add Professional Development section
                if 'professional_development' in candidate:
                    pd_data = candidate['professional_development']
                    f.write(f"   \n   PROFESSIONAL DEVELOPMENT:\n")
                    f.write(f"   Professional Development Score: {pd_data['professional_development_score']:.1%}\n")
                    f.write(f"   Level: {pd_data['professional_development_level']}\n")
                    
                    # Certifications
                    cert_data = pd_data['component_scores']['certifications']
                    if cert_data['certification_count'] > 0:
                        f.write(f"   Certifications: {cert_data['certification_count']} found\n")
                        if cert_data['certification_categories']:
                            f.write(f"     Categories: {', '.join(cert_data['certification_categories'].keys())}\n")
                        if cert_data['recent_certification_score'] > 0.7:
                            f.write(f"     ✓ Recent certifications (within 2 years)\n")
                    
                    # Online Learning
                    learning_data = pd_data['component_scores']['online_learning']
                    if learning_data['platforms_found']:
                        f.write(f"   Online Learning: {', '.join(learning_data['platforms_found'])}\n")
                        if learning_data['course_count_estimate'] > 0:
                            f.write(f"     Estimated courses: {learning_data['course_count_estimate']}\n")
                    
                    # Conferences
                    conf_data = pd_data['component_scores']['conferences']
                    if conf_data['conference_score'] > 0:
                        if conf_data['speaker_events']:
                            f.write(f"   ✓ Conference Speaker\n")
                        if conf_data['major_conferences']:
                            f.write(f"   Major Conferences: {', '.join(conf_data['major_conferences'])}\n")
                    
                    # Content Creation
                    content_data = pd_data['component_scores']['content_creation']
                    if content_data['content_creation_score'] > 0:
                        f.write(f"   Content Creation: {', '.join(content_data['content_platforms'])}\n")
                        if content_data.get('github_activity'):
                            f.write(f"     GitHub Activity: Active contributor\n")
                    
                    # Key Highlights
                    if pd_data['summary']['key_highlights']:
                        f.write(f"   Key Highlights:\n")
                        for highlight in pd_data['summary']['key_highlights']:
                            f.write(f"     • {highlight}\n")
                
                f.write(f"\n")
            
            f.write(f"\n{'='*70}\n")
            f.write(f"PROFESSIONAL DEVELOPMENT INSIGHTS:\n")
            f.write(f"{'='*70}\n")
            
            # Aggregate PD insights across all top candidates
            pd_insights = self._aggregate_pd_insights(results['final_top_5'])
            
            f.write(f"Continuous Learners: {pd_insights['continuous_learners']}/{len(results['final_top_5'])}\n")
            f.write(f"Cloud Certified: {pd_insights['cloud_certified']}/{len(results['final_top_5'])}\n")
            f.write(f"Conference Speakers: {pd_insights['speakers']}/{len(results['final_top_5'])}\n")
            f.write(f"Content Creators: {pd_insights['content_creators']}/{len(results['final_top_5'])}\n")
            f.write(f"Average PD Score: {pd_insights['avg_pd_score']:.1%}\n")
            
            f.write(f"\n{'='*70}\n")
            f.write(f"QUALITY ASSURANCE REVIEW:\n")
            f.write(f"{'='*70}\n")
            f.write(results['qa_review']['qa_assessment'])
        
        print(f"\n📄 Summary report created: {report_path}")
    
    def _aggregate_pd_insights(self, candidates: List[Dict]) -> Dict[str, Any]:
        """Aggregate professional development insights across candidates"""
        insights = {
            'continuous_learners': 0,
            'cloud_certified': 0,
            'speakers': 0,
            'content_creators': 0,
            'total_pd_score': 0.0,
            'avg_pd_score': 0.0
        }
        
        for candidate in candidates:
            if 'professional_development' in candidate:
                pd_data = candidate['professional_development']
                summary = pd_data['summary']
                
                if summary.get('continuous_learner'):
                    insights['continuous_learners'] += 1
                
                if 'cloud' in summary.get('certification_categories', []):
                    insights['cloud_certified'] += 1
                
                if summary.get('conference_speaker'):
                    insights['speakers'] += 1
                
                if summary.get('content_creator'):
                    insights['content_creators'] += 1
                
                insights['total_pd_score'] += pd_data['professional_development_score']
        
        if candidates:
            insights['avg_pd_score'] = insights['total_pd_score'] / len(candidates)
        
        return insights


class TicketTracker:
    """Track processed tickets to avoid reprocessing"""
    
    def __init__(self, tracking_file: str = None):
        if tracking_file:
            self.tracking_file = Path(tracking_file)
        else:
            # Auto-detect tracking file location
            current_dir = Path.cwd()
            if current_dir.name == 'approved_tickets':
                self.tracking_file = current_dir / '.processing_tracker.json'
            else:
                self.tracking_file = Path('approved_tickets/.processing_tracker.json')
        
        self.processed_tickets = self._load_tracking_data()
    
    def _load_tracking_data(self) -> Dict:
        """Load tracking data from file"""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_tracking_data(self):
        """Save tracking data to file"""
        # Ensure directory exists
        self.tracking_file.parent.mkdir(exist_ok=True)
        with open(self.tracking_file, 'w') as f:
            json.dump(self.processed_tickets, f, indent=2)
    
    def get_ticket_hash(self, ticket_folder: Path) -> str:
        """Generate a hash based on ticket content to detect changes"""
        hash_content = []
        
        # Include job details files
        for pattern in ['job_details.json', 'job-data.json', '*.json']:
            for json_file in ticket_folder.glob(pattern):
                if json_file.name not in ['metadata.json', 'applications.json'] and json_file.exists():
                    with open(json_file, 'r') as f:
                        hash_content.append(f.read())
                    break
        
        # Include number and names of resume files
        resume_files = []
        for ext in ['.pdf', '.docx', '.doc']:
            resume_files.extend([f.name for f in ticket_folder.glob(f"*{ext}")])
        
        resume_files.sort()
        hash_content.append(','.join(resume_files))
        
        # Generate hash
        content_str = ''.join(hash_content)
        return hashlib.md5(content_str.encode()).hexdigest()
    
    def is_ticket_processed(self, ticket_folder: Path) -> Tuple[bool, Optional[str]]:
        """Check if ticket has been processed and if content changed"""
        ticket_id = ticket_folder.name
        current_hash = self.get_ticket_hash(ticket_folder)
        
        if ticket_id in self.processed_tickets:
            stored_data = self.processed_tickets[ticket_id]
            stored_hash = stored_data.get('content_hash', '')
            
            if stored_hash == current_hash:
                return True, stored_data.get('last_processed')
            else:
                return False, "content_changed"
        
        return False, None
    
    def mark_ticket_processed(self, ticket_folder: Path, results_file: str):
        """Mark ticket as processed"""
        ticket_id = ticket_folder.name
        current_hash = self.get_ticket_hash(ticket_folder)
        
        self.processed_tickets[ticket_id] = {
            'content_hash': current_hash,
            'last_processed': datetime.now().isoformat(),
            'results_file': results_file,
            'status': 'completed'
        }
        
        self._save_tracking_data()
    
    def get_processing_summary(self) -> Dict:
        """Get summary of all processed tickets"""
        return {
            'total_processed': len(self.processed_tickets),
            'tickets': self.processed_tickets
        }
    
    def reset_ticket(self, ticket_id: str):
        """Reset a specific ticket to allow reprocessing"""
        if ticket_id in self.processed_tickets:
            del self.processed_tickets[ticket_id]
            self._save_tracking_data()
            return True
        return False
    
    def reset_all(self):
        """Reset all tracking data"""
        self.processed_tickets = {}
        self._save_tracking_data()


class BatchProcessor:
    """Process multiple job tickets in batch"""
    
    def __init__(self, jobs_folder: str = None):
        # Determine the jobs folder
        if jobs_folder:
            self.jobs_folder = Path(jobs_folder)
        else:
            # Check if we're already in approved_tickets folder
            current_dir = Path.cwd()
            if current_dir.name == 'approved_tickets':
                self.jobs_folder = current_dir
            else:
                self.jobs_folder = current_dir / 'approved_tickets'
        
        # Adjust tracking file path based on current location
        if self.jobs_folder.name == 'approved_tickets':
            tracking_file = self.jobs_folder / '.processing_tracker.json'
        else:
            tracking_file = 'approved_tickets/.processing_tracker.json'
        
        self.tracker = TicketTracker(str(tracking_file))
        self.results_summary = []
        
        # Create batch results folder
        self.batch_results_folder = self.jobs_folder / "batch_results"
        self.batch_results_folder.mkdir(exist_ok=True, parents=True)
    
    def get_all_tickets(self) -> List[Path]:
        """Get all ticket folders in approved_tickets"""
        tickets = []
        
        # Look for directories that contain job data
        for item in self.jobs_folder.iterdir():
            if item.is_dir() and not item.name.startswith('.') and item.name != 'batch_results':
                # Check if it contains job data files
                has_job_data = any([
                    (item / 'job_details.json').exists(),
                    (item / 'job-data.json').exists(),
                    (item / 'applications.json').exists()
                ])
                
                if has_job_data:
                    tickets.append(item)
        
        return sorted(tickets)
    
    def process_all_tickets(self, force_reprocess: bool = False, specific_tickets: List[str] = None):
        """Process all tickets in the jobs folder"""
        print(f"\n{'='*80}")
        print(f"🚀 BATCH RESUME FILTERING SYSTEM WITH DUPLICATE DETECTION")
        print(f"{'='*80}")
        
        all_tickets = self.get_all_tickets()
        
        if specific_tickets:
            # Filter to only specified tickets
            all_tickets = [t for t in all_tickets if t.name in specific_tickets]
        
        print(f"📁 Found {len(all_tickets)} ticket(s) in {self.jobs_folder}")
        
        if not all_tickets:
            print("❌ No valid job tickets found!")
            return
        
        # Summary tracking
        processed_count = 0
        skipped_count = 0
        error_count = 0
        
        # Process each ticket
        for i, ticket_folder in enumerate(all_tickets, 1):
            print(f"\n{'='*70}")
            print(f"📋 Processing Ticket {i}/{len(all_tickets)}: {ticket_folder.name}")
            print(f"{'='*70}")
            
            try:
                # Check if already processed
                is_processed, process_info = self.tracker.is_ticket_processed(ticket_folder)
                
                if is_processed and not force_reprocess:
                    print(f"✅ Already processed on: {process_info}")
                    print(f"   (Use --force to reprocess)")
                    skipped_count += 1
                    
                    # Load previous results for summary
                    self._add_to_summary(ticket_folder, "skipped", process_info)
                    continue
                
                if process_info == "content_changed":
                    print(f"🔄 Content changed since last processing. Reprocessing...")
                
                # Process the ticket
                print(f"🔍 Starting resume filtering for: {ticket_folder.name}")
                
                filter_system = UpdatedResumeFilteringSystem(str(ticket_folder))
                results = filter_system.filter_resumes()
                
                if "error" not in results:
                    # Mark as processed
                    results_file = filter_system.output_folder / f"final_results_{filter_system.job_ticket.ticket_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    self.tracker.mark_ticket_processed(ticket_folder, str(results_file))
                    
                    processed_count += 1
                    self._add_to_summary(ticket_folder, "completed", results)
                    
                    print(f"\n✅ Successfully processed ticket: {ticket_folder.name}")
                else:
                    error_count += 1
                    self._add_to_summary(ticket_folder, "error", results.get("error"))
                    print(f"\n❌ Error processing ticket: {results.get('error')}")
                
            except Exception as e:
                error_count += 1
                self._add_to_summary(ticket_folder, "error", str(e))
                print(f"\n❌ Error processing ticket {ticket_folder.name}: {str(e)}")
                import traceback
                traceback.print_exc()
            
            # Add delay between tickets to avoid API rate limits
            if i < len(all_tickets):
                print(f"\n⏳ Waiting 2 seconds before next ticket...")
                time.sleep(2)
        
        # Generate batch summary report
        self._generate_batch_summary(processed_count, skipped_count, error_count)
    
    def _add_to_summary(self, ticket_folder: Path, status: str, data: Any):
        """Add ticket result to summary"""
        summary_entry = {
            'ticket_id': ticket_folder.name,
            'ticket_path': str(ticket_folder),
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        
        if status == "completed" and isinstance(data, dict):
            summary_entry.update({
                'position': data.get('position', 'Unknown'),
                'total_resumes': data.get('summary', {}).get('total_resumes', 0),
                'unique_candidates': data.get('summary', {}).get('unique_candidates', 0),
                'duplicate_groups': data.get('summary', {}).get('duplicate_groups_found', 0),
                'top_5_selected': len(data.get('final_top_5', [])),
                'top_candidates': [
                    {
                        'name': c['filename'],
                        'score': f"{c['final_score']:.1%}",
                        'is_duplicate': c.get('has_duplicates', False)
                    }
                    for c in data.get('final_top_5', [])[:3]  # Top 3 for summary
                ]
            })
        elif status == "error":
            summary_entry['error_message'] = str(data)
        elif status == "skipped":
            summary_entry['last_processed'] = data
        
        self.results_summary.append(summary_entry)
    
    def _generate_batch_summary(self, processed: int, skipped: int, errors: int):
        """Generate comprehensive batch processing summary"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON summary
        json_summary = {
            'batch_run_timestamp': datetime.now().isoformat(),
            'statistics': {
                'total_tickets': processed + skipped + errors,
                'processed': processed,
                'skipped': skipped,
                'errors': errors
            },
            'tickets': self.results_summary,
            'tracker_summary': self.tracker.get_processing_summary()
        }
        
        json_file = self.batch_results_folder / f"batch_summary_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(json_summary, f, indent=2)
        
        # Text report
        report_file = self.batch_results_folder / f"batch_report_{timestamp}.txt"
        with open(report_file, 'w') as f:
            f.write(f"BATCH PROCESSING SUMMARY REPORT\n")
            f.write(f"{'='*80}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"\nSTATISTICS:\n")
            f.write(f"  Total Tickets: {processed + skipped + errors}\n")
            f.write(f"  Processed: {processed}\n")
            f.write(f"  Skipped (Already Processed): {skipped}\n")
            f.write(f"  Errors: {errors}\n")
            
            f.write(f"\n{'='*80}\n")
            f.write(f"TICKET DETAILS:\n")
            f.write(f"{'='*80}\n\n")
            
            for ticket in self.results_summary:
                f.write(f"Ticket ID: {ticket['ticket_id']}\n")
                f.write(f"Status: {ticket['status'].upper()}\n")
                
                if ticket['status'] == 'completed':
                    f.write(f"Position: {ticket.get('position', 'Unknown')}\n")
                    f.write(f"Resumes Processed: {ticket.get('total_resumes', 0)}\n")
                    f.write(f"Unique Candidates: {ticket.get('unique_candidates', 'N/A')}\n")
                    f.write(f"Duplicate Groups: {ticket.get('duplicate_groups', 0)}\n")
                    f.write(f"Top Candidates:\n")
                    for j, candidate in enumerate(ticket.get('top_candidates', []), 1):
                        dup_status = " (Duplicate)" if candidate.get('is_duplicate') else ""
                        f.write(f"  {j}. {candidate['name']} - {candidate['score']}{dup_status}\n")
                elif ticket['status'] == 'skipped':
                    f.write(f"Last Processed: {ticket.get('last_processed', 'Unknown')}\n")
                elif ticket['status'] == 'error':
                    f.write(f"Error: {ticket.get('error_message', 'Unknown error')}\n")
                
                f.write(f"\n{'-'*50}\n\n")
        
        # Print summary to console
        print(f"\n{'='*80}")
        print(f"📊 BATCH PROCESSING COMPLETE")
        print(f"{'='*80}")
        print(f"Total Tickets: {processed + skipped + errors}")
        print(f"✅ Processed: {processed}")
        print(f"⏭️  Skipped: {skipped}")
        print(f"❌ Errors: {errors}")
        print(f"\n📁 Batch results saved to: {self.batch_results_folder}")
        print(f"   - Summary: {json_file.name}")
        print(f"   - Report: {report_file.name}")
    
    def show_status(self):
        """Show status of all tickets"""
        all_tickets = self.get_all_tickets()
        tracking_data = self.tracker.get_processing_summary()
        
        print(f"\n{'='*80}")
        print(f"📊 JOB TICKETS STATUS")
        print(f"{'='*80}")
        print(f"Total Tickets Found: {len(all_tickets)}")
        print(f"Total Processed: {tracking_data['total_processed']}")
        print(f"\nTicket Details:")
        print(f"{'-'*80}")
        
        for ticket in all_tickets:
            ticket_id = ticket.name
            status = "❌ Not Processed"
            last_processed = "Never"
            
            if ticket_id in tracking_data['tickets']:
                status = "✅ Processed"
                last_processed = tracking_data['tickets'][ticket_id]['last_processed']
            
            print(f"{ticket_id:40} | {status:20} | Last: {last_processed}")


def main():
    """Main function with batch processing support"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Resume Filtering System with Duplicate Detection')
    parser.add_argument('ticket_folder', nargs='?', help='Specific ticket folder to process')
    parser.add_argument('--batch', action='store_true', help='Process all tickets in approved_tickets folder')
    parser.add_argument('--force', action='store_true', help='Force reprocess already processed tickets')
    parser.add_argument('--status', action='store_true', help='Show status of all tickets')
    parser.add_argument('--reset', type=str, help='Reset specific ticket ID to allow reprocessing')
    parser.add_argument('--reset-all', action='store_true', help='Reset all tracking data')
    parser.add_argument('--tickets', nargs='+', help='Process specific ticket IDs only')
    
    args = parser.parse_args()
    
    # Handle status command
    if args.status:
        processor = BatchProcessor()
        processor.show_status()
        return
    
    # Handle reset commands
    if args.reset_all:
        processor = BatchProcessor()
        processor.tracker.reset_all()
        print("✅ All tracking data has been reset")
        return
    
    if args.reset:
        processor = BatchProcessor()
        if processor.tracker.reset_ticket(args.reset):
            print(f"✅ Ticket {args.reset} has been reset")
        else:
            print(f"❌ Ticket {args.reset} not found in tracking data")
        return
    
    # Handle batch processing
    if args.batch:
        print("🚀 Starting batch processing of all tickets...")
        processor = BatchProcessor()
        processor.process_all_tickets(
            force_reprocess=args.force,
            specific_tickets=args.tickets
        )
        return
    
    # Handle single ticket processing
    if args.ticket_folder:
        ticket_folder = args.ticket_folder
    else:
        # If no arguments, show help
        parser.print_help()
        print("\n📋 Examples:")
        print("  Process single ticket:     python main.py approved_tickets/e206b5ae66_Re-Data-Engineer")
        print("  Process all tickets:       python main.py --batch")
        print("  Force reprocess all:       python main.py --batch --force")
        print("  Process specific tickets:  python main.py --batch --tickets e206b5ae66_Re-Data-Engineer")
        print("  Show status:              python main.py --status")
        print("  Reset ticket:             python main.py --reset e206b5ae66_Re-Data-Engineer")
        print("  Reset all:                python main.py --reset-all")
        return
    
    # Process single ticket
    if not os.path.exists(ticket_folder):
        print(f"❌ Error: Folder '{ticket_folder}' not found")
        return
    
    # Check if already processed
    tracker = TicketTracker()
    ticket_path = Path(ticket_folder)
    is_processed, info = tracker.is_ticket_processed(ticket_path)
    
    if is_processed and not args.force:
        print(f"✅ Ticket {ticket_path.name} already processed on: {info}")
        print(f"   Use --force to reprocess")
        return
    
    try:
        print("🚀 Initializing Resume Filtering System with Duplicate Detection...")
        filter_system = UpdatedResumeFilteringSystem(ticket_folder)
        
        results = filter_system.filter_resumes()
        
        if "error" not in results:
            # Mark as processed
            results_file = filter_system.output_folder / f"final_results_{filter_system.job_ticket.ticket_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            tracker.mark_ticket_processed(ticket_path, str(results_file))
            
            print(f"\n{'='*70}")
            print(f"✅ FILTERING COMPLETE - FINAL SUMMARY")
            print(f"{'='*70}")
            print(f"Total resumes processed: {results['summary']['total_resumes']}")
            print(f"Unique candidates identified: {results['summary']['unique_candidates']}")
            print(f"Duplicate groups found: {results['summary']['duplicate_groups_found']}")
            print(f"\nTop candidates:")
            for i, candidate in enumerate(results['final_top_5']):
                print(f"  {i+1}. {candidate['filename']}")
                print(f"      Score: {candidate['final_score']:.1%}")
                print(f"      Skills: {len(candidate['matched_skills'])}/{len(results['latest_requirements']['tech_stack'])} matched")
                print(f"      Experience: {candidate['detected_experience_years']} years")
                print(f"      Prof. Development: {candidate['professional_development_score']:.1%}")
                if candidate.get('has_duplicates'):
                    print(f"      ⚠️ Best of {candidate.get('duplicate_count', 1) + 1} submissions")
            
            print(f"\n📁 Results saved in: {filter_system.output_folder}")
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()