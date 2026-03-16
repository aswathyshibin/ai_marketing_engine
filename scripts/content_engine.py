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

    def refine_text(self, text: str, context: str = "marketing", max_words: int = 0) -> str:
        """Uses AI (NLP) to refine and professionalize sentences into high-status copy."""
        word_constraint = f" strictly enforced word count of MAX {max_words} WORDS" if max_words > 0 else ""
        prompt = f"""
        Refine the following {context} text into 'Magnetic' high-status marketing copy with{word_constraint}.
        Use sophisticated, professional vocabulary that attracts elite clients.
        Focus on clarity, authority, and professional impact.
        Avoid clichés; use power words that command attention.
        IMPORTANT: Your output MUST NOT exceed {max_words if max_words > 0 else 'a reasonable length'} words.
        
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

    def generate_marketing_bundle(self, course: Dict) -> Dict:
        """Generates captions, hashtags, and poster headline using Groq."""
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
        - "is_tech": boolean, true if it's a technical course.
        """

        chat_completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional social media marketer for Acadeno Technologies. You write high-converting copy.",
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
        bundle['poster_headline'] = self.refine_text(bundle['poster_headline'], "poster headline")
        bundle['caption'] = self.refine_text(bundle['caption'], "social media caption")
        
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
