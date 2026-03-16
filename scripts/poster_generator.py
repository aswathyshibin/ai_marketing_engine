import os
import asyncio
from playwright.async_api import async_playwright
from jinja2 import Template

class PosterGenerator:
    def __init__(self):
        self.template_path = os.path.join("templates", "poster_template.html")
        self.output_dir = os.path.join("output", "posters")
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate_poster(self, data: dict, filename: str):
        """Generates a poster from data using HTML/CSS and Playwright."""
        with open(self.template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        template = Template(template_content)
        rendered_html = template.render(
            audience=data.get("Target Audience", "Students"),
            course_name=data.get("course_name", data.get("Course", "New Course")),
            headline=data.get("poster_headline", "Build Your Future"),
            topic=data.get("Topic", "Learn New Skills"),
            cta=data.get("CTA", "Register Now"),
            logo_data=data.get("logo_data", ""),
            bg_url=data.get("bg_url", "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1080&q=80")
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1080, "height": 1080})
            await page.set_content(rendered_html)
            
            # Robust wait for all images to finish loading
            await page.wait_for_load_state('networkidle')
            await page.evaluate("() => Promise.all(Array.from(document.images).map(img => img.complete || new Promise(resolve => img.onload = img.onerror = resolve)))")
            
            output_path = os.path.join(self.output_dir, filename)
            await page.screenshot(path=output_path, full_page=True)
            await browser.close()
            return output_path

if __name__ == "__main__":
    test_data = {
        "Course": "AI Integrated Flutter Development",
        "Topic": "Build AI Mobile Apps",
        "Target Audience": "College Students",
        "CTA": "Join Now",
        "poster_headline": "MASTER AI MOBILE APPS WITH FLUTTER"
    }
    
    gen = PosterGenerator()
    asyncio.run(gen.generate_poster(test_data, "test_poster.png"))
    print(f"Test poster generated in: {gen.output_dir}")
