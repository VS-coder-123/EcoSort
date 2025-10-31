import os
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class WasteClassifier:
    def __init__(self):
        """Initialize the Gemini model with API key from environment variables."""
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in environment variables. "
                "Please set it in your .env file."
            )
        
        # Configure the Gemini API
        genai.configure(api_key=self.api_key)
        
        # Initialize the model with the latest vision-capable model
        try:
            # Use gemini-2.5-flash which supports vision and is optimized for speed
            self.model_name = 'gemini-2.5-flash'
            self.model = genai.GenerativeModel(self.model_name)
            print(f"✅ Initialized {self.model_name} model successfully")
        except Exception as e:
            print(f"⚠️  Could not initialize gemini-2.5-flash, falling back to gemini-2.0-flash: {str(e)}")
            try:
                self.model_name = 'gemini-2.0-flash'
                self.model = genai.GenerativeModel(self.model_name)
                print("✅ Initialized gemini-2.0-flash model successfully")
            except Exception as e2:
                print(f"⚠️  Could not initialize gemini-2.0-flash, falling back to gemini-pro-vision: {str(e2)}")
                self.model = genai.GenerativeModel('gemini-pro-vision')
                print("✅ Initialized gemini-pro-vision model successfully")
        
        # Define waste categories and disposal advice
        self.waste_categories = {
            'biodegradable': {
                'wet': {
                    'description': 'Biodegradable Wet Waste',
                    'advice': '✅ Compost this item or place it in the green bin.\n\n' \
                             '💡 Tip: These materials break down naturally and can be composted ' \
                             'to create nutrient-rich soil.'
                },
                'dry': {
                    'description': 'Biodegradable Dry Waste',
                    'advice': '♻️ Compost or dispose in green bin.\n\n' \
                             '💡 Tip: These items will decompose naturally but may take longer ' \
                             'than wet waste. Shredding can speed up the process.'
                }
            },
            'non-biodegradable': {
                'wet': {
                    'description': 'Non-Biodegradable Wet Waste',
                    'advice': '⚠️ Dry before disposal. Check local recycling guidelines.\n\n' \
                             '💡 Tip: Clean and dry these items before recycling to prevent ' \
                             'contamination of other recyclables.'
                },
                'dry': {
                    'description': 'Non-Biodegradable Dry Waste',
                    'advice': '🔄 Recycle if possible, otherwise dispose safely.\n\n' \
                             '💡 Tip: Check for local recycling programs. When in doubt, ' \
                             'consult your local waste management guidelines.'
                }
            }
        }
    
    def classify_waste(self, image_input):
        """
        Classify waste image into categories and provide disposal advice.
        
        Args:
            image_input (str, Path, or file-like object): Path to the image file or a file-like object
            
        Returns:
            dict: Classification results with category and disposal advice
        """
        try:
            # Enhanced prompt with detailed classification
            prompt = """
            Analyze this waste item and provide a detailed classification based on the following criteria:
            
            1. Primary Category (choose one):
               - Organic (food waste, plant material, paper products)
               - Recyclable (plastics, glass, metals, paper/cardboard)
               - Hazardous (batteries, electronics, chemicals)
               - General Waste (non-recyclable, non-hazardous items)
            
            2. Secondary Category (be specific, e.g., 'plastic bottle', 'food container', 'paper'):
               - Be specific about the material and form
               
            3. Biodegradability (choose one):
               - biodegradable
               - non-biodegradable
               
            4. Moisture content (choose one):
               - wet
               - dry
            
            5. Confidence level (high/medium/low)
            
            Return ONLY a JSON object with the following structure:
            {
                "primary_category": "chosen primary category",
                "secondary_category": "specific item type",
                "biodegradable": "biodegradable or non-biodegradable",
                "moisture": "wet or dry",
                "item_name": "common name of the item",
                "confidence": "high/medium/low",
                "disposal_advice": "specific disposal instructions"
            }
            """
            
            # Handle both file paths and file-like objects
            if hasattr(image_input, 'read') and callable(image_input.read):
                # It's a file-like object
                try:
                    # Make sure we have a fresh copy of the data
                    if hasattr(image_input, 'getvalue'):
                        # It's a BytesIO or similar
                        image_data = image_input.getvalue()
                    else:
                        # For other file-like objects, read the data
                        if hasattr(image_input, 'seek') and callable(image_input.seek):
                            image_input.seek(0)
                        image_data = image_input.read()
                        
                        # Reset the file pointer if possible
                        if hasattr(image_input, 'seek') and callable(image_input.seek):
                            image_input.seek(0)
                    
                    # Create the image part for the API
                    image_part = {
                        "mime_type": "image/jpeg",
                        "data": image_data
                    }
                    
                except Exception as e:
                    raise ValueError(f"Error reading image data: {str(e)}")
            else:  # It's a file path (string or Path object)
                try:
                    image_path = Path(image_input)
                    if not image_path.exists():
                        raise FileNotFoundError(f"Image not found: {image_path}")
                    with open(image_path, 'rb') as f:
                        image_data = f.read()
                    image_part = {
                        "mime_type": "image/jpeg",
                        "data": image_data
                    }
                except (TypeError, AttributeError, OSError) as e:
                    raise ValueError(f"Invalid image input: {e}")
            
            # Generate content with proper error handling
            try:
                response = self.model.generate_content([
                    prompt,
                    image_part
                ], 
                generation_config={
                    "temperature": 0.1,  # Lower temperature for more focused responses
                    "max_output_tokens": 1024,
                })
                
                # Check if the response was blocked
                if not response.text or not response.text.strip():
                    raise ValueError("Empty or blocked response from the model")
                    
            except Exception as e:
                error_msg = f"Error generating content: {str(e)}"
                if hasattr(e, 'response') and hasattr(e.response, 'text'):
                    error_msg += f"\nResponse: {e.response.text}"
                raise RuntimeError(error_msg)
            
            # Parse the response
            try:
                # Extract JSON from the response
                import json
                import re
                
                # Clean the response text to extract JSON
                response_text = response.text.strip()
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                
                if not json_match:
                    raise ValueError("Could not parse model response as JSON")
                    
                result = json.loads(json_match.group(0))
                
                # Validate the response structure
                required_keys = [
                    'primary_category', 'secondary_category', 
                    'biodegradable', 'moisture', 'item_name', 
                    'confidence', 'disposal_advice'
                ]
                if not all(key in result for key in required_keys):
                    raise ValueError(f"Missing required keys in response: {result}")
                
                # Normalize the response
                bio_key = result['biodegradable'].lower()
                moisture_key = result['moisture'].lower()
                primary_category = result['primary_category'].lower()
                secondary_category = result['secondary_category'].lower()
                
                # Get the waste category and advice
                if bio_key in self.waste_categories and moisture_key in self.waste_categories[bio_key]:
                    category_info = self.waste_categories[bio_key][moisture_key]
                else:
                    # Fallback to general advice if specific category not found
                    category_info = {
                        'description': primary_category.capitalize(),
                        'advice': result.get('disposal_advice', 'Please check local recycling guidelines.')
                    }
                
                # Format the response with enhanced information
                return {
                    'success': True,
                    'item_name': result['item_name'],
                    'primary_category': primary_category,
                    'secondary_category': secondary_category,
                    'biodegradable': bio_key,
                    'moisture': moisture_key,
                    'confidence': result['confidence'].lower(),
                    'disposal_advice': result.get('disposal_advice', category_info.get('advice', '')),
                    'category': category_info['description'],
                    'advice': category_info['advice']
                }
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                error_msg = f"Error processing model response: {str(e)}"
                if 'response_text' in locals():
                    # Ensure response_text is a string
                    response_text_str = str(response_text) if response_text else "No response text"
                    error_msg += f"\n\nResponse was:\n{response_text_str}"
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            error_msg = str(e)
            # Add more context to common errors
            if "quota" in error_msg.lower():
                error_msg += "\n\n💡 You may have exceeded your API quota. Please check your Google Cloud Console for quota limits."
            elif "image" in error_msg.lower() and "invalid" in error_msg.lower():
                error_msg += "\n\n💡 The provided image might be corrupted or in an unsupported format. Please try with a different image."
            elif "blocked" in error_msg.lower():
                error_msg += "\n\n⚠️  The content was blocked by the safety filters. Please try with a different image."
                
            return {
                'success': False,
                'error': f"Error classifying image: {error_msg}"
            }
