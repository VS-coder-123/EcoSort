import os
import io
import json
import traceback
from flask import Flask, render_template, request, jsonify, send_from_directory
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after loading environment variables
from src.prediction import WastePrediction
from src.model import WasteClassifier

app = Flask(__name__, template_folder='templates', static_folder='static')

def get_classifier():
    """Initialize and return the classifier."""
    try:
        print("Initializing WasteClassifier...")
        classifier = WasteClassifier()
        print("WasteClassifier initialized successfully")
        return classifier
    except Exception as e:
        error_msg = f"❌ Failed to initialize classifier: {str(e)}"
        print(error_msg)
        print("Traceback:", traceback.format_exc())
        return None

# Initialize the classifier
classifier = get_classifier()

# Create static directory if it doesn't exist
os.makedirs('static/uploads', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/classify', methods=['POST'])
def classify():
    try:
        print("\n=== New Classification Request ===")  # Debug log
        print(f"Request headers: {dict(request.headers)}")  # Debug log
        print(f"Request form data: {request.form}")  # Debug log
        
        # Check if the post request has the file part
        if 'file' not in request.files:
            error_msg = "No file part in the request"
            print(f"❌ {error_msg}")  # Debug log
            return jsonify({'success': False, 'error': error_msg}), 400
            
        file = request.files['file']
        
        # If user does not select file, browser also submit an empty part without filename
        if file.filename == '':
            error_msg = 'No selected file'
            print(f"❌ {error_msg}")  # Debug log
            return jsonify({'success': False, 'error': error_msg}), 400
            
        print(f"📄 File received: {file.filename}")  # Debug log
        file_data = file.read()
        print(f"📏 File size: {len(file_data)} bytes")  # Debug log
        file = io.BytesIO(file_data)  # Create a new file-like object from the data
        
        # Validate the image
        print("🔍 Validating image...")  # Debug log
        is_valid, validation_result = WastePrediction.validate_image(file)
        if not is_valid:
            error_msg = f"Invalid image: {validation_result}"
            print(f"❌ {error_msg}")  # Debug log
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Update file with the validated file-like object
        file = validation_result
        file.seek(0)
        
        # Get the classifier
        print("🤖 Initializing classifier...")  # Debug log
        classifier = get_classifier()
        if not classifier:
            error_msg = "Failed to initialize classifier"
            print(f"❌ {error_msg}")  # Debug log
            return jsonify({'success': False, 'error': error_msg}), 500
            
        # Classify the image
        print("\n🔮 Starting Image Classification")  # Debug log
        print(f"📊 Using model: {classifier.model_name}")
        print("🔄 Processing image...")  # Debug log
        
        try:
            # Create a new BytesIO object for classification
            classification_data = io.BytesIO(file_data)
            print("Created BytesIO object for classification")  # Debug log
            
            # Log model info
            if hasattr(classifier, 'model') and hasattr(classifier.model, 'model_name'):
                print(f"Using model: {classifier.model.model_name}")  # Debug log
            
            # Reset the file pointer to the beginning
            classification_data.seek(0)
            
            # Use the model to generate content
            response = classifier.model.generate_content([
                "Classify this image of waste into one of these categories: \n"
                "1. Biodegradable (wet/dry)\n"
                "2. Recyclable (paper/plastic/metal/glass)\n"
                "3. E-waste\n"
                "4. Hazardous\n"
                "5. Non-recyclable\n\n"
                "Return the response in JSON format with these fields:\n"
                "- category: The primary waste category\n"
                "- confidence: Your confidence level (0-100)\n"
                "- reason: A brief explanation\n"
                "- disposal_advice: How to properly dispose of this item",
                {"mime_type": "image/jpeg", "data": classification_data.read()}
            ])
            
            # Extract the text response
            result_text = response.text
            print(f"✅ Classification completed. Result: {result_text}")  # Debug log
            
            # Parse the JSON response
            try:
                # Clean up the response text
                clean_text = result_text.strip()
                if '```json' in clean_text:
                    clean_text = clean_text.split('```json', 1)[1].rsplit('```', 1)[0].strip()
                
                print(f"📝 Raw response text: {clean_text}")  # Debug log
                
                result = json.loads(clean_text)
                print(f"✅ Parsed JSON result: {result}")  # Debug log
                
                # Ensure required fields exist
                if not all(key in result for key in ['category', 'confidence']):
                    raise ValueError("Missing required fields in the response")
                
                primary_category = result.get('category', 'Unknown')
                confidence = int(result.get('confidence', 0))
                
                # Generate a secondary category based on the primary
                secondary_categories = {
                    'plastic': 'Recyclable (paper)',
                    'paper': 'Recyclable (plastic)',
                    'metal': 'Recyclable (glass)',
                    'glass': 'Recyclable (metal)',
                    'biodegradable': 'Compostable',
                    'hazardous': 'Special Disposal',
                    'e-waste': 'Electronic Waste'
                }
                
                # Find a secondary category that's different from the primary
                secondary_category = next(
                    (v for k, v in secondary_categories.items() 
                     if k.lower() not in primary_category.lower()),
                    'General Waste'  # Default secondary category
                )
                
                # Calculate secondary confidence (slightly lower than primary)
                secondary_confidence = max(0, min(100, confidence - 10))
                
                # Prepare the response
                response_data = {
                    'success': True,
                    'primary_category': primary_category,
                    'primary_confidence': confidence,
                    'secondary_category': secondary_category,
                    'secondary_confidence': secondary_confidence,
                    'combined_category': f"{primary_category} / {secondary_category}",
                    'is_biodegradable': 'biodegradable' in primary_category.lower(),
                    'disposal_advice': result.get('disposal_advice', 'No specific disposal advice available.')
                }
                
                print(f"✅ Successfully prepared response: {response_data}")  # Debug log
                
                return jsonify(response_data)
                
            except json.JSONDecodeError as je:
                error_msg = f"Failed to parse JSON response: {str(je)}"
                print(f"❌ {error_msg}")
                print(f"Raw response: {result_text}")
                return jsonify({
                    'success': False,
                    'error': 'Invalid response from the classification service',
                    'details': str(je)
                }), 500
                
        except Exception as e:
            error_msg = f"Error during classification: {str(e)}"
            print(f"❌ {error_msg}")
            print("Traceback:", traceback.format_exc())
            return jsonify({
                'success': False,
                'error': 'Error during classification',
                'details': str(e),
                'type': type(e).__name__
            }), 500

            # Get detailed classification from the model
            try:
                classification_prompt = """
                Analyze this waste item thoroughly and provide detailed information in JSON format:
                {
                    "item_name": "common name of the item (be specific)",
                    "is_biodegradable": true/false,  // true if the item can decompose naturally
                    "moisture_status": "wet" or "dry",  // current state of the item
                    "material_type": "organic/plastic/metal/paper/glass/other",
                    "features": [
                        "material composition",
                        "size/weight if notable",
                        "color",
                        "brand or markings if visible",
                        "any damage or wear",
                        "other distinguishing characteristics"
                    ],
                    "composition_breakdown": {
                        "material": "detailed material description",
                        "components": ["list of main components"],
                        "potential_recyclability": "high/medium/low"
                    },
                    "confidence": "high/medium/low"
                }
                
                IMPORTANT: 
                - Be extremely specific about the item's name and features
                - Include as many relevant details as possible
                - For features, provide 3-5 most important characteristics
                - For composition, break down the materials if possible
                - If the item is a container, note if it's empty or contains residue
                """
                
                # Get the model's response for detailed classification
                response = classifier.model.generate_content([
                    classification_prompt,
                    image_part
                ], generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 500,
                })
                
                # Parse the response
                try:
                    # Clean the response and extract JSON
                    response_text = response.text.strip()
                    if '```json' in response_text:
                        response_text = response_text.split('```json')[1].split('```')[0].strip()
                    elif '```' in response_text:
                        response_text = response_text.split('```')[1].strip()
                    
                    classification = json.loads(response_text)
                    print(f"Raw classification from model: {classification}")
                    
                    # Set primary classification (biodegradable status)
                    is_biodegradable = classification.get('is_biodegradable', False)
                    primary_category = "Biodegradable" if is_biodegradable else "Non-biodegradable"
                    
                    # Set secondary classification (wet/dry)
                    moisture_status = classification.get('moisture_status', 'dry').lower()
                    secondary_category = "Wet" if 'wet' in moisture_status else "Dry"
                    
                    # Get item details
                    item_name = classification.get('item_name', 'Unknown Item')
                    material_type = classification.get('material_type', 'other')
                    
                    # Format features for display
                    features = classification.get('features', [])
                    if not isinstance(features, list):
                        features = [str(features)] if features else []
                    
                    # Get composition details
                    composition = classification.get('composition_breakdown', {})
                    material_desc = composition.get('material', material_type)
                    components = composition.get('components', [])
                    recyclability = composition.get('potential_recyclability', 'medium')
                    
                    # Create detailed object info
                    object_details = [
                        f"<div class='mb-2'><strong>{item_name}</strong></div>",
                        f"<div class='text-sm mb-2'>Material: <span class='font-medium'>{material_desc}</span></div>"
                    ]
                    
                    if features:
                        features_text = ("<div class='text-sm'><strong>Features:</strong> " +
                                      ", ".join([f for f in features if f and str(f).strip()]) +
                                      "</div>")
                        object_details.append(features_text)
                    
                    if components:
                        components_text = ", ".join(
                            [f"<span class='bg-gray-100 px-2 py-1 rounded'>{c}</span>" for c in components if c]
                        )
                        object_details.append(
                            f"<div class='mt-2 text-sm'><strong>Components:</strong> "
                            f"<div class='flex flex-wrap gap-1 mt-1'>{components_text}</div></div>"
                        )
                    
                    # Format features as a clean list
                    clean_features = []
                    for feature in features:
                        if feature and str(feature).strip():
                            clean_features.append(f"• {str(feature).strip()}")
                    
                    # Add to result with clean, frontend-ready data
                    result.update({
                        'is_biodegradable': is_biodegradable,
                        'moisture': moisture_status,
                        'item_name': item_name,
                        'features': clean_features,
                        'material_type': material_type,
                        'recyclability': recyclability,
                        'object_details': "".join(object_details)  # Keep for backward compatibility
                    })
                    
                except Exception as e:
                    print(f"⚠️ Error parsing classification: {str(e)}")
                    print(f"Raw response: {response_text}")
                    raise ValueError("Failed to parse classification response")
                
            except Exception as e:
                print(f"⚠️  Could not get detailed classification: {str(e)}")
                print("Falling back to default classification")
                primary_category = "Biodegradable"
                secondary_category = "Dry"
                item_name = "Waste Item"
                features_text = "No features identified"
            
            # Prepare the prediction result with all required fields
            formatted_for_prediction = {
                'success': True,
                'item_name': result.get('item_name', 'Unknown Item'),
                'features': result.get('features', 'No features identified'),
                'confidence': 'high' if confidence > 70 else 'medium' if confidence > 30 else 'low',
                'biodegradable': 'biodegradable' if result.get('is_biodegradable', False) else 'non-biodegradable',
                'moisture': result.get('moisture', 'dry'),
                'advice': result.get('disposal_advice', 'No specific advice available.'),
                'primary_category': 'Biodegradable' if result.get('is_biodegradable', False) else 'Non-biodegradable',
                'primary_confidence': confidence,
                'secondary_category': 'Wet' if result.get('moisture', 'dry') == 'wet' else 'Dry',
                'secondary_confidence': max(0, min(100, confidence - 5)),
                'combined_category': f"{result.get('material_type', 'Waste').title()}: {result.get('item_name', 'Item')}",
                'is_biodegradable': result.get('is_biodegradable', False),
                'disposal_advice': result.get('disposal_advice', 'No specific disposal advice available for this item.')
            }
            
            print(f"Formatted prediction: {json.dumps(formatted_for_prediction, indent=2)}")
            
            # Format the result for display
            print("Formatting result...")  # Debug log
            formatted_result = WastePrediction.format_classification_result(formatted_for_prediction)
            print(f"Formatted result type: {type(formatted_result)}")  # Debug log
            print(f"Formatted result content: {formatted_result}")  # Debug log
            
            if not isinstance(formatted_result, dict):
                error_msg = f"Unexpected result format: {type(formatted_result)}"
                print(f"❌ {error_msg}")  # Debug log
                return jsonify({
                    'success': False,
                    'error': 'Invalid classification result format',
                    'details': error_msg
                }), 500
            
            if not formatted_result.get('success', False):
                error_msg = formatted_result.get('error', 'Classification failed')
                print(f"❌ Classification failed: {error_msg}")  # Debug log
                return jsonify({
                    'success': False,
                    'error': 'Classification failed',
                    'details': error_msg
                }), 500
                
                # Get the primary classification (biodegradable/non-biodegradable)
                is_biodegradable = formatted_result.get('is_biodegradable', False)
                primary_category = 'Biodegradable' if is_biodegradable else 'Non-biodegradable'
                primary_confidence = int(formatted_result.get('primary_confidence', 95))
                
                # Get the secondary classification (wet/dry)
                moisture = formatted_result.get('moisture', 'dry').capitalize()
                secondary_category = f"{moisture}"
                secondary_confidence = int(formatted_result.get('secondary_confidence', primary_confidence - 5))
                
                # Get item details
                item_name = formatted_result.get('item_name', 'Unknown Item')
                features = formatted_result.get('features', 'No features identified')
                
                # Prepare the response with all required fields
                response_data = {
                    'success': True,
                    'primary_category': primary_category,
                    'primary_confidence': primary_confidence,
                    'secondary_category': secondary_category,
                    'secondary_confidence': secondary_confidence,
                    'item_name': item_name,
                    'features': features,
                    'is_biodegradable': is_biodegradable,
                    'disposal_advice': formatted_result.get('disposal_advice', 'No specific disposal advice available.'),
                    'combined_category': f"{primary_category} ({moisture})"
                }
                
                print(f"✅ Successfully prepared response: {response_data}")  # Debug log
                
                return jsonify(response_data)
                
        except Exception as e:
            error_msg = f"❌ Error during classification: {str(e)}"
            print(error_msg)  # Debug log
            print("Traceback:", traceback.format_exc())  # Debug log
            return jsonify({
                'success': False,
                'error': 'Error during classification',
                'details': str(e),
                'type': type(e).__name__
            }), 500
            
        except Exception as e:
            print(f"Error during classification: {str(e)}")  # Debug log
            print("Traceback:", traceback.format_exc())  # Debug log
            return jsonify({
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
            
    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Debug log
        print("Traceback:", traceback.format_exc())  # Debug log
        return jsonify({
            'error': 'An unexpected error occurred',
            'details': str(e),
            'traceback': traceback.format_exc()
        }), 500
    finally:
        # Clean up any resources
        if 'validation_data' in locals():
            validation_data.close()
        if 'classification_data' in locals():
            classification_data.close()

if __name__ == '__main__':
    # Create static/js directory if it doesn't exist
    os.makedirs('static/js', exist_ok=True)
    
    # Run the Flask app on port 8001
    app.run(debug=True, port=8001, host='0.0.0.0')
