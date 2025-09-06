"""
CSV service for import/export operations
"""
import io
import csv
import uuid
from typing import List, Optional, Dict, Any
import pandas as pd
from fastapi import UploadFile, HTTPException

from app.services.card_service import CardService
from app.schemas.schemas import CardCreate, CSVImportResponse


class CSVService:
    def __init__(self, card_service: CardService):
        self.card_service = card_service
    
    async def import_cards_from_csv(
        self, 
        deck_id: uuid.UUID,
        file: UploadFile,
        validate_only: bool = False
    ) -> CSVImportResponse:
        """Import cards from CSV file"""
        try:
            # Read CSV content
            content = await file.read()
            
            # Reset file pointer
            await file.seek(0)
            
            # Parse CSV
            try:
                # Try to decode as UTF-8 first
                csv_content = content.decode('utf-8')
            except UnicodeDecodeError:
                # Fallback to UTF-8 with error handling
                csv_content = content.decode('utf-8', errors='replace')
            
            # Parse CSV data
            reader = csv.DictReader(io.StringIO(csv_content))
            
            cards_data = []
            errors = []
            line_number = 1  # Header is line 1
            
            for row in reader:
                line_number += 1
                
                # Validate required fields
                if not all(field in row for field in ['hanzi', 'pinyin', 'english']):
                    errors.append(f"Line {line_number}: Missing required fields (hanzi, pinyin, english)")
                    continue
                
                # Clean and validate data
                hanzi = row['hanzi'].strip()
                pinyin = row['pinyin'].strip()
                english = row['english'].strip()
                
                if not hanzi or not pinyin or not english:
                    errors.append(f"Line {line_number}: Empty values not allowed")
                    continue
                
                # Create card data
                card_data = CardCreate(
                    hanzi=hanzi,
                    pinyin=pinyin,
                    english=english
                )
                
                cards_data.append(card_data)
            
            if not cards_data and not errors:
                errors.append("No valid card data found in CSV file")
            
            # If validation only, return results without importing
            if validate_only:
                return CSVImportResponse(
                    success=len(errors) == 0,
                    imported_count=0,
                    errors=errors,
                    validated_cards=cards_data
                )
            
            # Import cards if no validation errors
            imported_count = 0
            if not errors:
                for card_data in cards_data:
                    try:
                        card = await self.card_service.create_card(deck_id, card_data)
                        if card:
                            imported_count += 1
                        else:
                            errors.append(f"Failed to create card: {card_data.hanzi}")
                    except Exception as e:
                        errors.append(f"Error creating card {card_data.hanzi}: {str(e)}")
            
            return CSVImportResponse(
                success=imported_count > 0 and len(errors) == 0,
                imported_count=imported_count,
                errors=errors
            )
            
        except Exception as e:
            return CSVImportResponse(
                success=False,
                imported_count=0,
                errors=[f"File processing error: {str(e)}"]
            )
    
    async def import_cards_from_pandas(
        self,
        deck_id: uuid.UUID,
        file: UploadFile,
        validate_only: bool = False
    ) -> CSVImportResponse:
        """Import cards using pandas for better CSV handling"""
        try:
            # Read file content
            content = await file.read()
            
            # Use pandas to read CSV with better encoding handling
            try:
                df = pd.read_csv(io.BytesIO(content), encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(content), encoding='latin1')
            
            # Validate columns
            required_columns = ['hanzi', 'pinyin', 'english']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return CSVImportResponse(
                    success=False,
                    imported_count=0,
                    errors=[f"Missing required columns: {', '.join(missing_columns)}"]
                )
            
            cards_data = []
            errors = []
            
            for index, row in df.iterrows():
                line_number = index + 2  # +2 because index starts at 0 and we have a header
                
                # Check for NaN values
                if pd.isna(row['hanzi']) or pd.isna(row['pinyin']) or pd.isna(row['english']):
                    errors.append(f"Line {line_number}: Missing values not allowed")
                    continue
                
                # Clean data
                hanzi = str(row['hanzi']).strip()
                pinyin = str(row['pinyin']).strip()
                english = str(row['english']).strip()
                
                if not hanzi or not pinyin or not english:
                    errors.append(f"Line {line_number}: Empty values not allowed")
                    continue
                
                # Create card data
                try:
                    card_data = CardCreate(
                        hanzi=hanzi,
                        pinyin=pinyin,
                        english=english
                    )
                    cards_data.append(card_data)
                except Exception as e:
                    errors.append(f"Line {line_number}: Invalid data - {str(e)}")
            
            # If validation only
            if validate_only:
                return CSVImportResponse(
                    success=len(errors) == 0,
                    imported_count=0,
                    errors=errors,
                    validated_cards=cards_data
                )
            
            # Import cards
            imported_count = 0
            if not errors:
                for card_data in cards_data:
                    try:
                        card = await self.card_service.create_card(deck_id, card_data)
                        if card:
                            imported_count += 1
                        else:
                            errors.append(f"Failed to create card: {card_data.hanzi}")
                    except Exception as e:
                        errors.append(f"Error creating card {card_data.hanzi}: {str(e)}")
            
            return CSVImportResponse(
                success=imported_count > 0,
                imported_count=imported_count,
                errors=errors
            )
            
        except Exception as e:
            return CSVImportResponse(
                success=False,
                imported_count=0,
                errors=[f"File processing error: {str(e)}"]
            )
    
    async def export_deck_to_csv(
        self, 
        deck_id: uuid.UUID,
        include_stats: bool = False,
        user_id: Optional[uuid.UUID] = None
    ) -> str:
        """Export deck cards to CSV format"""
        try:
            # Get all cards in the deck
            cards = await self.card_service.get_deck_cards(deck_id)
            
            if not cards:
                return ""
            
            # Prepare CSV data
            output = io.StringIO()
            
            if include_stats and user_id:
                # Include user statistics
                fieldnames = ['hanzi', 'pinyin', 'english', 'flip_count', 'quiz_attempts', 'quiz_correct', 'accuracy_rate', 'mastery_level']
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                for card in cards:
                    # Get card with progress
                    card_with_progress = await self.card_service.get_card_with_progress(card.id, user_id)
                    
                    row = {
                        'hanzi': card.hanzi,
                        'pinyin': card.pinyin,
                        'english': card.english,
                        'flip_count': 0,
                        'quiz_attempts': 0,
                        'quiz_correct': 0,
                        'accuracy_rate': 0.0,
                        'mastery_level': 0
                    }
                    
                    if card_with_progress and card_with_progress.user_progress:
                        progress = card_with_progress.user_progress
                        row.update({
                            'flip_count': progress.flip_count,
                            'quiz_attempts': progress.quiz_attempts,
                            'quiz_correct': progress.quiz_correct,
                            'accuracy_rate': progress.accuracy_rate or 0.0,
                            'mastery_level': progress.mastery_level
                        })
                    
                    writer.writerow(row)
            else:
                # Basic export without statistics
                fieldnames = ['hanzi', 'pinyin', 'english']
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                for card in cards:
                    writer.writerow({
                        'hanzi': card.hanzi,
                        'pinyin': card.pinyin,
                        'english': card.english
                    })
            
            csv_content = output.getvalue()
            output.close()
            
            return csv_content
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")
    
    async def export_deck_to_pandas_csv(
        self,
        deck_id: uuid.UUID,
        include_stats: bool = False,
        user_id: Optional[uuid.UUID] = None
    ) -> bytes:
        """Export deck to CSV using pandas for better formatting"""
        try:
            # Get all cards in the deck
            cards = await self.card_service.get_deck_cards(deck_id)
            
            if not cards:
                return b""
            
            # Prepare data for DataFrame
            data = []
            
            for card in cards:
                row = {
                    'hanzi': card.hanzi,
                    'pinyin': card.pinyin,
                    'english': card.english
                }
                
                if include_stats and user_id:
                    # Get card progress
                    card_with_progress = await self.card_service.get_card_with_progress(card.id, user_id)
                    
                    if card_with_progress and card_with_progress.user_progress:
                        progress = card_with_progress.user_progress
                        row.update({
                            'flip_count': progress.flip_count,
                            'quiz_attempts': progress.quiz_attempts,
                            'quiz_correct': progress.quiz_correct,
                            'accuracy_rate': round(progress.accuracy_rate or 0.0, 3),
                            'mastery_level': progress.mastery_level
                        })
                    else:
                        row.update({
                            'flip_count': 0,
                            'quiz_attempts': 0,
                            'quiz_correct': 0,
                            'accuracy_rate': 0.0,
                            'mastery_level': 0
                        })
                
                data.append(row)
            
            # Create DataFrame and convert to CSV
            df = pd.DataFrame(data)
            
            # Convert to CSV bytes
            csv_buffer = io.BytesIO()
            df.to_csv(csv_buffer, index=False, encoding='utf-8')
            csv_buffer.seek(0)
            
            return csv_buffer.getvalue()
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")
    
    def validate_csv_format(self, content: str) -> List[str]:
        """Validate CSV format and return any errors"""
        errors = []
        
        try:
            reader = csv.DictReader(io.StringIO(content))
            
            # Check for required headers
            if not reader.fieldnames:
                errors.append("CSV file appears to be empty or invalid")
                return errors
            
            required_fields = ['hanzi', 'pinyin', 'english']
            missing_fields = [field for field in required_fields if field not in reader.fieldnames]
            
            if missing_fields:
                errors.append(f"Missing required columns: {', '.join(missing_fields)}")
            
            # Check first few rows for basic validation
            row_count = 0
            for row in reader:
                row_count += 1
                if row_count > 5:  # Only check first 5 rows for validation
                    break
                
                for field in required_fields:
                    if field in row and not row[field].strip():
                        errors.append(f"Row {row_count + 1}: Empty {field} value")
            
            if row_count == 0:
                errors.append("CSV file contains no data rows")
                
        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")
        
        return errors