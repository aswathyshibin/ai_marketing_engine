import os
import pandas as pd
from typing import List, Dict
from groq import Groq
from dotenv import load_dotenv

load_dotenv(override=True)

class ContentEngine:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        self.client = Groq(api_key=self.api_key)
        self.courses_path = os.path.join("data", "courses.csv")

    def load_courses(self) -> List[Dict]:
        """Loads course data from CSV."""
        if not os.path.exists(self.courses_path):
            return []
        df = pd.read_csv(self.courses_path)
        return df.to_dict('records')

    def refine_text(self, text: str, context: str = "marketing", max_words: int = 0, **kwargs) -> str:
        """Uses AI (NLP) to refine and professionalize sentences into high-status copy."""
        word_constraint = f" strictly enforced word count of MAX {max_words} WORDS" if max_words > 0 else ""
        language = kwargs.get('language', 'english')
        malayalam_rules = ""
        if language.lower() == "malayalam":
            malayalam_rules = """
        IMPORTANT: You MUST write the output in Malayalam. Use natural, conversational 'Manglish' style (English technical terms written in Malayalam script). 
        EXAMPLE: Instead of 'ബൃഹത്തായ ഡാറ്റ വിശ്ലേഷണം', use 'ഡാറ്റ അനലിറ്റിക്സ് മാസ്റ്ററി'. 
        Keep words like 'AI', 'Course', 'Career', 'Success' in English sounds but write them in Malayalam script. 
        Avoid 'pure' textbook Malayalam. Stay in Malayalam script.
            """

        prompt = f"""
        Refine the following {context} text into 'Magnetic' high-status marketing copy with{word_constraint}.
        Use sophisticated, professional vocabulary that attracts elite clients.
        Focus on clarity, authority, and professional impact.
        Avoid clichés; use power words that command attention.
        IMPORTANT: Your output MUST NOT exceed {max_words if max_words > 0 else 'a reasonable length'} words.
        {f"The output MUST be in {language}." if language != 'english' else "The output MUST be in English."}
        {malayalam_rules}
        
        Text to refine: {text}
        
        Return ONLY the refined text string.
        """
        
        try:
            completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
            )
            return completion.choices[0].message.content.strip().strip('"')
        except:
            return text

    def generate_marketing_bundle(self, course: Dict, language: str = "english") -> Dict:
        """Generates captions, hashtags, and poster headline using Groq."""
        malayalam_rules = ""
        if language.lower() == "malayalam":
            malayalam_rules = """
        IMPORTANT: If the language is Malayalam, use natural, conversational 'Manglish' style. 
        Keep technical words (like 'Data Analytics', 'AI', 'Full Stack', 'Course', 'Career', 'Future', 'Enroll') as English sounds but written in Malayalam script. 
        EXAMPLE: 'ഡാറ്റ അനലിറ്റിക്സ് കരിയർ സക്സസ്' (Data Analytics Career Success) is better than pure translations.
        Do NOT use pure formal translations.
            """

        prompt = f"""
        Generate a professional social media marketing bundle for the following course:
        Course: {course['Course']}
        Topic: {course['Topic']}
        Target Audience: {course['Target Audience']}
        CTA: {course['CTA']}

        Return the response in strictly JSON format with the following keys:
        - "caption": A short, motivational caption for Instagram/LinkedIn.
        - "hashtags": A string of 5 relevant hashtags.
        - "poster_headline": An ultra-short, punchy headline (MAXIMUM 3 WORDS).
        - "video_script": {{
            "scenes": [
              {{"text": "First 4-5 seconds of dialogue", "keyword": "image search keyword"}},
              {{"text": "Next 4-5 seconds of dialogue", "keyword": "image search keyword"}},
              {{"text": "Final 4-5 seconds of dialogue and CTA", "keyword": "image search keyword"}}
            ]
          }},
        - "visual_keyword": A single English word describing the visual theme of this topic (e.g. 'coding', 'finance', 'cybersecurity').
        
        IMPORTANT: All text content (caption, headline) MUST be in {language}. {malayalam_rules}
        CRITICAL RULE FOR VIDEO: The "video_script" dialogue text MUST ALWAYS BE IN ENGLISH, even if the requested language is Malayalam. This is strictly required for the AI Voice System.
        """

        chat_completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f"You are a professional social media marketer for Acadeno Technologies. You write high-converting copy.{' Return ONLY Malayalam text.' if language == 'malayalam' else ''}",
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
        )

        import json
        bundle = json.loads(chat_completion.choices[0].message.content)
        
        # NLP Refinement for each generated text component
        bundle['poster_headline'] = self.refine_text(bundle['poster_headline'], "poster headline", language=language)
        bundle['caption'] = self.refine_text(bundle['caption'], "social media caption", language=language)
        
        return bundle

if __name__ == "__main__":
    engine = ContentEngine()
    courses = engine.load_courses()
    if courses:
        print(f"Loaded {len(courses)} courses.")
        test_course = courses[0]
        print(f"Generating content for: {test_course['Course']}")
        bundle = engine.generate_marketing_bundle(test_course)
        print(json.dumps(bundle, indent=2))
