import os
import httpx
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Recruiter Chat API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
client = MongoClient(MONGODB_URI)
db = client.recruiter_chat
chats_collection = db.chats

# Pydantic models
class Message(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[datetime] = None

class RecruiterInfo(BaseModel):
    company: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    session_id: str
    recruiter_info: Optional[RecruiterInfo] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

# Your personal information - CUSTOMIZE THIS!
CANDIDATE_INFO = """
Name: [Your Full Name]
Current Role: [Your Current Position]
Experience: [Years] years in [Your Field]

Key Skills:
- [Skill 1 - e.g., Python, JavaScript, React]
- [Skill 2 - e.g., Machine Learning, Data Analysis]
- [Skill 3 - e.g., Cloud Computing, AWS, Docker]
- [Add more relevant skills]

Recent Experience:
- [Company Name]: [Your Role] ([Duration - e.g., 2022-Present])
  • [Key achievement or responsibility]
  • [Another achievement with metrics if possible]
  
- [Previous Company]: [Previous Role] ([Duration])
  • [Key achievement]
  • [Another achievement]

Education:
- [Degree] in [Field] from [University] ([Year])
- [Any relevant certifications or additional education]

Notable Projects:
- [Project 1]: [Brief description and technologies used]
- [Project 2]: [Brief description and impact/results]

Interests: [What type of roles/companies you're interested in]
Location: [Your location and remote work preferences]
Availability: [Current availability status]

Instructions for AI: 
You are representing this candidate to recruiters. Be professional, enthusiastic, and highlight relevant experience based on what the recruiter is asking about. Answer questions about their background, skills, and experience. If you don't have specific information about something, politely indicate that the recruiter can reach out directly to the candidate for more details. Always be honest about the candidate's experience and don't exaggerate. Be helpful in understanding if there might be a good fit for their role.
"""

# Groq API integration
async def get_chat_response(messages: List[dict]) -> str:
    """Get response from Groq API"""
    
    # Prepare messages for the API
    api_messages = [
        {"role": "system", "content": CANDIDATE_INFO}
    ]
    api_messages.extend(messages)
    
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise HTTPException(status_code=500, detail="Groq API key not configured")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-8b-instant",  # Free model
                    "messages": api_messages,
                    "max_tokens": 1000,
                    "temperature": 0.7
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Groq API error: {response.text}"
                )
                
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request timeout")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error calling Groq API: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Recruiter Chat API is running!"}

@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat_endpoint(request: Request, chat_request: ChatRequest):
    """Main chat endpoint"""
    
    try:
        # Get existing conversation or create new one
        chat_doc = chats_collection.find_one({"session_id": chat_request.session_id})
        
        if chat_doc is None:
            # Create new chat session
            chat_doc = {
                "session_id": chat_request.session_id,
                "messages": [],
                "recruiter_info": chat_request.recruiter_info.dict() if chat_request.recruiter_info else {},
                "created_at": datetime.utcnow()
            }
            chats_collection.insert_one(chat_doc)
        
        # Add user message
        user_message = {
            "role": "user",
            "content": chat_request.message,
            "timestamp": datetime.utcnow()
        }
        
        # Prepare messages for AI (last 10 messages to keep context manageable)
        messages_for_ai = chat_doc["messages"][-10:] if chat_doc["messages"] else []
        messages_for_ai.append({"role": "user", "content": chat_request.message})
        
        # Get AI response
        ai_response = await get_chat_response(messages_for_ai)
        
        # Create assistant message
        assistant_message = {
            "role": "assistant", 
            "content": ai_response,
            "timestamp": datetime.utcnow()
        }
        
        # Update database
        chats_collection.update_one(
            {"session_id": chat_request.session_id},
            {
                "$push": {
                    "messages": {
                        "$each": [user_message, assistant_message]
                    }
                },
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return ChatResponse(response=ai_response, session_id=chat_request.session_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.command("ping")
        return {"status": "healthy", "timestamp": datetime.utcnow()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
