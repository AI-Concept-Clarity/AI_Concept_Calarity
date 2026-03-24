# AI_Concept_Calarity
An AI-powered web application that explains scientific terms in simple language using LLaMA models, featuring voice input, smart search history, and a professional Flask-based architecture.


# ConceptClarity
### Scientific Terminology Explainer  
(Infosys Springboard Virtual Internship 6.0)

ConceptClarity is a web-based AI-powered application designed to explain scientific terms in simple, beginner-friendly language. The project emphasizes clarity, accessibility, clean UI design, and professional backend architecture.

---

## Milestone 1: UI Foundation & Input Handling

### Description
The first milestone focused on building a strong foundation for the application, including a modern user interface, robust input validation, and accessibility considerations.

### Key Features
- Professional, responsive two-panel UI design
- Clean alignment and spacing with mobile-first responsiveness
- Input validation for empty, numeric-only, and invalid terms
- User-friendly success and error feedback messages
- Voice input using browser Speech Recognition API
- Accessible components with ARIA attributes
- Stable layout with reserved space for dynamic content

### Outcome
A polished and accessible frontend capable of accepting both text and voice input, validating user queries, and providing clear feedback, meeting professional UI/UX standards.

---



## Milestone 2: AI Integration & Smart History Management

### Description
The second milestone introduced AI-based explanation generation and a fully functional, professional search history system.

### Key Features
- Integration with Groq API using LLaMA-based language models
- Structured prompt engineering for concise, beginner-friendly explanations
- Session-based search history with unique identifiers
- Automatic grouping of history into Today, Yesterday, and Earlier
- Inline rename and delete functionality (ChatGPT-style)
- Click-to-rerun history searches
- Keyboard navigation for history (↑ ↓ Enter)
- POST-Redirect-GET (PRG) pattern to prevent form resubmission issues
- Backward-compatible session handling to avoid runtime errors

### Outcome
A stable and intelligent system that generates meaningful explanations and manages user search history in a professional, production-ready manner.

---

## Current Status
Milestone 1 and Milestone 2 are completed successfully, delivering a clean UI, reliable AI explanations, and an advanced, user-friendly history management system.
