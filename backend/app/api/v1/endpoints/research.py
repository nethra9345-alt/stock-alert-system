"""API Endpoints for Stage 7: AI-Powered Stock Research & Intelligent Investment Assistant."""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.schemas.research import (
    ResearchChatRequest,
    ResearchChatResponse,
    StockComparisonRequest,
    CreateReportRequest,
    ReportListItem,
)
from backend.app.services.market_service import normalize_symbol
from backend.app.services.fundamentals import get_company_fundamentals
from backend.app.services.technical_analysis import analyze_technical_structure
from backend.app.services.stock_comparison import compare_stocks
from backend.app.services.rag_retrieval import retrieve_rag_context
from backend.app.services.llm_assistant import process_research_chat, get_chat_history
from backend.app.services.report_generator import generate_research_report, get_saved_reports, get_report_by_id

router = APIRouter()


@router.get("/{symbol}")
def get_stock_research_dossier(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieves full verified RAG research dossier including quote, fundamentals, technicals, and events."""
    norm_sym = normalize_symbol(symbol)
    context = retrieve_rag_context(norm_sym, db=db, user_id=current_user.id, include_portfolio=False)
    return context


@router.get("/{symbol}/fundamentals")
def get_fundamentals_endpoint(
    symbol: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieves audited company fundamentals, valuation multiples, and financial health ratios."""
    norm_sym = normalize_symbol(symbol)
    return get_company_fundamentals(norm_sym)


@router.get("/{symbol}/technical")
def get_technical_analysis_endpoint(
    symbol: str,
    period: str = Query("6mo", description="Historical period for technical analysis"),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieves technical indicator synthesis, pivot support/resistance levels, and directional signals."""
    norm_sym = normalize_symbol(symbol)
    return analyze_technical_structure(norm_sym, period=period)


@router.post("/chat", response_model=ResearchChatResponse)
async def chat_research_endpoint(
    req: ResearchChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Handles an interactive conversational research turn with RAG retrieval and persistence."""
    try:
        res = await process_research_chat(
            db=db,
            user_id=current_user.id,
            session_id=req.session_id,
            message=req.message,
            symbol=req.symbol,
            include_portfolio=req.include_portfolio,
        )
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research chat error: {str(e)}",
        )


@router.get("/chat/history")
def get_chat_history_endpoint(
    session_id: str = Query(..., description="Chat session ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Retrieves conversational history for a specific research session."""
    return get_chat_history(db=db, user_id=current_user.id, session_id=session_id)


@router.post("/compare")
def compare_stocks_endpoint(
    req: StockComparisonRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Performs multi-stock comparative analysis across fundamentals, technicals, and normalized performance."""
    try:
        res = compare_stocks(symbols=req.symbols, period=req.period)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Comparison failed: {str(e)}")


@router.post("/reports")
def create_report_endpoint(
    req: CreateReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Generates an institutional 9-section research report and persists it to the database."""
    try:
        res = generate_research_report(
            db=db,
            symbol=req.symbol,
            user_id=current_user.id,
            custom_title=req.title,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Report generation error: {str(e)}")


@router.get("/reports", response_model=List[ReportListItem])
def list_reports_endpoint(
    symbol: Optional[str] = Query(None, description="Optional symbol filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Lists saved research reports for the current user."""
    return get_saved_reports(db=db, user_id=current_user.id, symbol=symbol)


@router.get("/reports/{report_id}")
def get_report_detail_endpoint(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieves complete 9-section saved research report by ID."""
    rep = get_report_by_id(db=db, report_id=report_id, user_id=current_user.id)
    if not rep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research report not found.")
    return rep

