# MFL Carousel Generator

Generate high-quality Instagram carousel slides for Spanish (and optional Italian) language learning content, focused on natural phrasing, real-life usage, and common mistakes.

---

## Overview

This project is a full-stack content generator that creates ready-to-use language-learning carousels, including:

- Daily usable phrases  
- Common mistakes (correction-focused content)  
- Native vs textbook phrasing  
- English ↔ target language translation slides  

Designed for:
- Language learning content creators  
- MFL teachers  
- Educational social media accounts  

---

## Features

- AI-powered content generation (Claude)
- Spanish-first, with optional Italian support
- Focus on real-world, natural language
- Pre-built carousel slide templates
- Structured content formats:
  - Phrase-based posts
  - Mistake-based posts
  - Native phrasing comparisons
- Automatic English ↔ translation slides
- HTML to image rendering for social media
- Deployment-ready (e.g. Railway)

---

## Content Philosophy

This is not a traditional language-learning tool.

It prioritises:

- Natural phrasing over literal translation  
- Real usage over grammar theory  
- Simplicity over completeness  

Each carousel is designed to communicate one clear, practical idea.

---

## Example Carousel Flow

### Mistake Post

1. Hook  
   "Stop saying this in Spanish"

2. Mistake  
   Estoy caliente (incorrect in this context)

3. Correction  
   Tengo calor

4. Explanation  
   Short, intuitive reasoning

5. Example  
   Tengo calor hoy

6. Call to action  
   Save for later

---

### Phrase Post

1. Hook  
   "How to say: ‘I’m just looking’"

2. Translation Slide  
   EN: I’m just looking  
   ES: Solo estoy mirando  

3. Explanation  
   When and how it is used

4. Example  
   Real-life sentence

5. Call to action  

---

## Project Structure

```
.
├── app.py
├── generator.py
├── renderer.py
├── main.py
├── templates/
│   ├── slide-first.html
│   ├── slide-content.html
│   ├── slide-translate.html
│   └── slide-last.html
├── frontend/
│   ├── App.jsx
│   ├── Form.jsx
│   └── Output.jsx
├── railway.json
└── requirements.txt
```

---

## Setup

### 1. Clone the repository

```
git clone https://github.com/yourusername/mfl-carousel-generator.git
cd mfl-carousel-generator
```

---

### 2. Install dependencies

```
pip install -r requirements.txt
```

---

### 3. Set environment variables

Create a `.env` file:

```
CLAUDE_API_KEY=your_api_key_here
```

---

### 4. Run locally

```
python main.py
```

---

## Deployment (Railway)

This project is designed for straightforward deployment on Railway.

Steps:

1. Push the repository to GitHub  
2. Create a new project on Railway  
3. Link the repository  
4. Add required environment variables:
   - CLAUDE_API_KEY  

Railway will:
- Build the project  
- Inject the PORT environment variable  
- Run `python main.py`  

---

## Slide System

The generator maps structured content to visual templates:

- slide-first.html: Hook  
- slide-content.html: Explanation and examples  
- slide-translate.html: English to target language  
- slide-last.html: Call to action  

Supports:
- Cursive emphasis for key phrases  
- Underlining for key insights  
- Language flags (Spain / Italy)  
- Slide numbering  

---

## Example Input

```
Topic: "being hot"
Language: Spanish
Level: beginner
Type: mistake
```

### Output

- Incorrect: Estoy caliente  
- Correct: Tengo calor  

---

## Future Improvements

- Additional language support  
- Custom tone and style control  
- Batch generation  
- Scheduling and posting integration  
- Engagement analytics  

---

## Contributing

Contributions are welcome. For significant changes, please open an issue first.

---

## License

MIT License

---

## Notes

- Optimised for Instagram carousel content  
- Designed for high engagement and educational clarity  
- Focused on practical usage rather than completeness
