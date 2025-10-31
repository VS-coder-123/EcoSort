from PIL import Image, UnidentifiedImageError
import io
import os

class WastePrediction:
    """Handles waste prediction results and provides formatted outputs."""
    
    @staticmethod
    def validate_image(image_file):
        """
        Validate the uploaded image file and return a file-like object.
        
        Args:
            image_file: File-like object or path to image
            
        Returns:
            tuple: (is_valid, message_or_file_like_object)
        """
        buffer = None
        try:
            # If it's a file-like object
            if hasattr(image_file, 'read'):
                try:
                    # Reset file pointer if possible
                    if hasattr(image_file, 'seek'):
                        image_file.seek(0)
                    
                    # Read the file content
                    image_data = image_file.read()
                    
                    # Check if the file is empty
                    if not image_data:
                        return False, "The uploaded file is empty."
                    
                    # Check file size (max 5MB)
                    if len(image_data) > 5 * 1024 * 1024:  # 5MB
                        return False, "Image size should be less than 5MB."
                    
                    # Create a new BytesIO object with the image data
                    image_buffer = io.BytesIO(image_data)
                    
                    # Verify the image can be opened and is a supported format
                    try:
                        img = Image.open(image_buffer)
                        # Check if the format is supported
                        if img.format.lower() not in ['jpeg', 'jpg', 'png', 'webp']:
                            return False, f"Unsupported image format: {img.format}. Please upload a JPG, PNG, or WebP image."
                        
                        # Convert to RGB if necessary (for PNG with transparency)
                        if img.mode in ('RGBA', 'P'):
                            img = img.convert('RGB')
                        
                        # Create a new buffer with the processed image
                        processed_buffer = io.BytesIO()
                        img.save(processed_buffer, format='JPEG', quality=90)
                        processed_buffer.seek(0)
                        
                        return True, processed_buffer
                        
                    except UnidentifiedImageError:
                        return False, "The uploaded file is not a valid image."
                    except Exception as e:
                        return False, f"Error processing image: {str(e)}"
                    finally:
                        # Clean up the original buffer
                        if 'image_buffer' in locals():
                            image_buffer.close()
                
                except Exception as e:
                    return False, f"Error reading image: {str(e)}"
                
            # If it's a file path
            elif isinstance(image_file, str) and os.path.exists(image_file):
                try:
                    # Check file extension first
                    file_ext = os.path.splitext(image_file)[1].lower()
                    if file_ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                        return False, f"Unsupported file format: {file_ext}. Please upload a JPG, PNG, or WebP image."
                    
                    # Check file size (max 5MB)
                    if os.path.getsize(image_file) > 5 * 1024 * 1024:  # 5MB
                        return False, "Image size should be less than 5MB."
                        
                    # Verify it's a valid image
                    with Image.open(image_file) as img:
                        # Convert to RGB if necessary
                        if img.mode in ('RGBA', 'P'):
                            img = img.convert('RGB')
                        
                        # Save to a buffer
                        buffer = io.BytesIO()
                        img.save(buffer, format='JPEG', quality=90)
                        buffer.seek(0)
                        
                        return True, buffer
                        
                except UnidentifiedImageError:
                    return False, "The uploaded file is not a valid image."
                except Exception as e:
                    return False, f"Error processing image: {str(e)}"
                    
            else:
                return False, "Invalid file or file path provided."
                
        except Exception as e:
            # Clean up any open file-like objects
            if buffer is not None and hasattr(buffer, 'close'):
                try:
                    buffer.close()
                except:
                    pass
            return False, f"Error validating image: {str(e)}"
    
    @staticmethod
    def cleanup_temp_files():
        """Clean up any temporary files that were created."""
        temp_path = ".temp_uploaded_image.jpg"
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            print(f"Warning: Could not remove temporary file {temp_path}: {str(e)}")
    
    @staticmethod
    def format_classification_result(result):
        """
        Format the classification result for display.
        
        Args:
            result (dict): Classification result from WasteClassifier
            
        Returns:
            dict: Formatted result for display
        """
        if not result.get('success', False):
            return {
                'success': False,
                'error': result.get('error', 'Unknown error occurred')
            }
        
        # Format confidence with emoji
        confidence_map = {
            'high': '🔵 High',
            'medium': '🟢 Medium',
            'low': '🟠 Low'
        }
        
        # Get category emojis
        category_emojis = {
            'organic': '🌱',
            'recyclable': '♻️',
            'hazardous': '⚠️',
            'general': '🗑️'
        }
        
        confidence = result.get('confidence', 'low').lower()
        confidence_display = confidence_map.get(confidence, '🟠 Low')
        
        # Get primary and secondary categories
        primary_category = result.get('primary_category', 'general').lower()
        secondary_category = result.get('secondary_category', 'waste').title()
        
        # Get appropriate emoji for the category
        category_emoji = category_emojis.get(primary_category, '🗑️')
        
        # Format moisture and biodegradability
        moisture_emoji = '💧' if result.get('moisture') == 'wet' else '☀️'
        bio_emoji = '♻️' if 'biodegradable' in result.get('biodegradable', '') else '⛔'
        
        # Format the display strings
        primary_display = f"{category_emoji} {primary_category.title()}"
        secondary_display = f"📦 {secondary_category}"
        
        # Get disposal advice or use default
        advice = result.get('disposal_advice', result.get('advice', 'No specific advice available.'))
        
        return {
            'success': True,
            'item_name': result.get('item_name', 'Unknown item').title(),
            'primary_category': primary_display,
            'secondary_category': secondary_display,
            'biodegradable': f"{bio_emoji} {result.get('biodegradable', 'unknown').title()}",
            'moisture': f"{moisture_emoji} {result.get('moisture', 'unknown').title()}",
            'confidence': confidence_display,
            'advice': advice,
            'raw_data': result  # Include raw data for debugging
        }
    
    @staticmethod
    def cleanup_temp_files(temp_path):
        """
        Clean up temporary files created during processing.
        
        Args:
            temp_path (str): Path to the temporary file to remove
        """
        try:
            if temp_path and os.path.exists(temp_path) and temp_path.startswith('.temp_'):
                os.remove(temp_path)
        except Exception as e:
            # Don't raise error during cleanup
            pass
