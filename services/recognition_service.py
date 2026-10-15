import torch
import clip
from PIL import Image
import numpy as np

class RecognitionService:
    """
    CLIP-based object recognition and embedding extraction.
    """
    def __init__(self, device=None):
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[RecognitionService] Initializing on {self.device}...")
        
        # Load CLIP ViT-B/32
        self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
        self.model.eval()
        
        # Define educational categories
        self.category_prompts = {
            "geometry": "a 3d model of a geometric shape like sphere cube cylinder cone pyramid torus",
            "biology": "a 3d model of a biological structure like cell dna protein virus organ heart brain skeleton",
            "chemistry": "a 3d model of a chemical molecule or atom structure",
            "physics": "a 3d model of a physics apparatus like gear pulley lever magnet circuit engine",
            "lab": "a 3d model of laboratory equipment like microscope beaker flask test tube centrifuge",
            "tools": "a 3d model of a learning tool like ruler calculator pencil book compass notebook",
            "earth": "a 3d model of earth science like globe planet moon telescope map topography",
            "botany": "a 3d model of a plant structure like leaf flower root seed plant cell",
            "history": "a 3d model of a historical artifact fossil dinosaur ancient tool pottery"
        }
        
        # Precompute text embeddings for categories
        self.category_names = list(self.category_prompts.keys())
        text_tokens = clip.tokenize(list(self.category_prompts.values())).to(self.device)
        with torch.no_grad():
            self.category_features = self.model.encode_text(text_tokens)
            self.category_features /= self.category_features.norm(dim=-1, keepdim=True)

    @torch.no_grad()
    def recognize(self, pil_image):
        """
        Extracts image embedding and classifies category.
        """
        # Preprocess and encode image
        image = self.preprocess(pil_image).unsqueeze(0).to(self.device)
        image_features = self.model.encode_image(image)
        image_features /= image_features.norm(dim=-1, keepdim=True)
        
        # Compute similarity with category prompts
        similarity = (100.0 * image_features @ self.category_features.T).softmax(dim=-1)
        probs = similarity[0].cpu().numpy()
        
        top_idx = probs.argmax()
        category = self.category_names[top_idx]
        confidence = float(probs[top_idx])
        
        # Get top-5 candidates
        top5 = sorted(zip(self.category_names, probs), key=lambda x: -x[1])[:5]
        
        return {
            'embedding': image_features[0].cpu().numpy().astype(np.float32),
            'category': category,
            'confidence': confidence,
            'top5': top5
        }
