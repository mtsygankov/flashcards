"""
CSV import/export API routes
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response
from fastapi.responses import StreamingResponse
import io

from app.services.csv_service import CSVService
from app.services.card_service import CardService
from app.services.deck_service import DeckService
from app.auth.dependencies import get_current_active_user
from app.core.database import get_supabase_client
from app.schemas.schemas import CSVImportResponse

router = APIRouter(prefix="/csv", tags=["csv"])


async def get_csv_service() -> CSVService:
    """Dependency to get CSV service"""
    supabase_client = get_supabase_client()
    card_service = CardService(supabase_client)
    return CSVService(card_service)


async def get_deck_service() -> DeckService:
    """Dependency to get deck service"""
    supabase_client = get_supabase_client()
    return DeckService(supabase_client)


@router.post("/import/{deck_id}", response_model=CSVImportResponse)
async def import_cards_csv(
    deck_id: uuid.UUID,
    file: UploadFile = File(...),
    validate_only: bool = False,
    current_user: dict = Depends(get_current_active_user),
    csv_service: CSVService = Depends(get_csv_service),
    deck_service: DeckService = Depends(get_deck_service)
):
    """Import cards from CSV file"""
    
    # Verify deck belongs to user
    deck = await deck_service.get_deck_by_id(deck_id, uuid.UUID(current_user["id"]))
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    # Validate file type
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )
    
    # Import cards
    try:
        result = await csv_service.import_cards_from_pandas(
            deck_id=deck_id,
            file=file,
            validate_only=validate_only
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.post("/validate/{deck_id}", response_model=CSVImportResponse)
async def validate_csv_import(
    deck_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user),
    csv_service: CSVService = Depends(get_csv_service),
    deck_service: DeckService = Depends(get_deck_service)
):
    """Validate CSV file without importing"""
    
    # Verify deck belongs to user
    deck = await deck_service.get_deck_by_id(deck_id, uuid.UUID(current_user["id"]))
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    # Validate file type
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )
    
    # Validate CSV
    try:
        result = await csv_service.import_cards_from_pandas(
            deck_id=deck_id,
            file=file,
            validate_only=True
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.get("/export/{deck_id}")
async def export_deck_csv(
    deck_id: uuid.UUID,
    include_stats: bool = False,
    current_user: dict = Depends(get_current_active_user),
    csv_service: CSVService = Depends(get_csv_service),
    deck_service: DeckService = Depends(get_deck_service)
):
    """Export deck cards to CSV file"""
    
    # Verify deck belongs to user
    deck = await deck_service.get_deck_by_id(deck_id, uuid.UUID(current_user["id"]))
    if not deck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deck not found"
        )
    
    try:
        # Export cards
        user_id = uuid.UUID(current_user["id"]) if include_stats else None
        csv_bytes = await csv_service.export_deck_to_pandas_csv(
            deck_id=deck_id,
            include_stats=include_stats,
            user_id=user_id
        )
        
        # Create filename
        filename_suffix = "_with_stats" if include_stats else ""
        filename = f"{deck.name.replace(' ', '_')}{filename_suffix}.csv"
        
        # Return CSV as downloadable file
        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


@router.get("/template")
async def download_csv_template():
    """Download CSV template file"""
    
    template_content = """hanzi,pinyin,english
你好,nǐ hǎo,hello
谢谢,xiè xiè,thank you
再见,zài jiàn,goodbye
学习,xué xí,to study
中文,zhōng wén,Chinese language
"""
    
    return StreamingResponse(
        io.BytesIO(template_content.encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=flashcard_template.csv"}
    )


@router.post("/bulk-export")
async def bulk_export_all_decks(
    include_stats: bool = False,
    current_user: dict = Depends(get_current_active_user),
    csv_service: CSVService = Depends(get_csv_service),
    deck_service: DeckService = Depends(get_deck_service)
):
    """Export all user decks to a single CSV file"""
    
    try:
        # Get all user decks
        user_id = uuid.UUID(current_user["id"])
        decks = await deck_service.get_user_decks(user_id)
        
        if not decks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No decks found"
            )
        
        # Combine all deck data
        all_cards_data = []
        
        for deck in decks:
            # Add deck name to CSV data
            deck_cards_csv = await csv_service.export_deck_to_pandas_csv(
                deck_id=deck.id,
                include_stats=include_stats,
                user_id=user_id if include_stats else None
            )
            
            if deck_cards_csv:
                # Parse the CSV and add deck name
                import pandas as pd
                df = pd.read_csv(io.BytesIO(deck_cards_csv))
                df['deck_name'] = deck.name
                all_cards_data.append(df)
        
        if not all_cards_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No cards found in any deck"
            )
        
        # Combine all DataFrames
        combined_df = pd.concat(all_cards_data, ignore_index=True)
        
        # Reorder columns to put deck_name first
        cols = ['deck_name'] + [col for col in combined_df.columns if col != 'deck_name']
        combined_df = combined_df[cols]
        
        # Convert to CSV
        csv_buffer = io.BytesIO()
        combined_df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_buffer.seek(0)
        
        # Create filename
        filename_suffix = "_with_stats" if include_stats else ""
        filename = f"all_decks{filename_suffix}.csv"
        
        return StreamingResponse(
            csv_buffer,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk export failed: {str(e)}"
        )