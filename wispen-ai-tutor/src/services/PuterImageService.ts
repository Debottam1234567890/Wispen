/**
 * Puter Image Service
 * Generates images using Puter.js in the browser (where it works for free!)
 * Images are then uploaded to Firebase for video assembly.
 */

// Ensure Puter.js is loaded (add to index.html: <script src="https://js.puter.com/v2/"></script>)
declare const puter: {
    ai: {
        txt2img: (prompt: string, options?: { model?: string; quality?: string }) => Promise<HTMLImageElement>;
    };
};

export interface GeneratedImage {
    sceneIndex: number;
    prompt: string;
    imageUrl: string; // Firebase Storage URL
    base64?: string;
}

/**
 * Generate a single image using Puter in the browser
 */
export async function generateImageWithPuter(
    prompt: string,
    model: string = "black-forest-labs/FLUX.1-schnell"
): Promise<string> {
    // Check if puter is available
    if (typeof puter === 'undefined' || !puter.ai) {
        throw new Error('Puter.js not loaded. Add <script src="https://js.puter.com/v2/"></script> to index.html');
    }

    console.log(`[Puter] Generating image: "${prompt.substring(0, 50)}..."`);

    const img = await puter.ai.txt2img(prompt, { model });

    // Convert HTMLImageElement to base64
    return new Promise((resolve, reject) => {
        if (img.complete) {
            resolve(imageToBase64(img));
        } else {
            img.onload = () => resolve(imageToBase64(img));
            img.onerror = () => reject(new Error('Failed to load generated image'));
        }
    });
}

/**
 * Convert HTMLImageElement to base64 data URL
 */
function imageToBase64(img: HTMLImageElement): string {
    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth || img.width;
    canvas.height = img.naturalHeight || img.height;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Could not get canvas context');
    ctx.drawImage(img, 0, 0);
    return canvas.toDataURL('image/png');
}

/**
 * Upload a base64 image to Firebase Storage
 */
export async function uploadImageToFirebase(
    base64Data: string,
    sessionId: string,
    sceneIndex: number
): Promise<string> {
    const { getStorage, ref, uploadString, getDownloadURL } = await import('firebase/storage');
    const { getApp } = await import('firebase/app');

    const storage = getStorage(getApp());
    const imagePath = `video_frames/${sessionId}/scene_${sceneIndex}.png`;
    const storageRef = ref(storage, imagePath);

    // Upload base64 (remove data URL prefix)
    const base64Content = base64Data.replace(/^data:image\/\w+;base64,/, '');
    await uploadString(storageRef, base64Content, 'base64');

    // Get download URL
    const downloadUrl = await getDownloadURL(storageRef);
    console.log(`[Firebase] Uploaded scene ${sceneIndex}: ${downloadUrl.substring(0, 50)}...`);

    return downloadUrl;
}

/**
 * Generate all images for a video using Puter, upload to Firebase
 * Returns array of Firebase URLs ready for video assembly
 */
export async function generateAllImagesForVideo(
    scenes: Array<{ prompt: string; narration: string }>,
    sessionId: string,
    onProgress?: (current: number, total: number, status: string) => void
): Promise<string[]> {
    const imageUrls: string[] = [];

    for (let i = 0; i < scenes.length; i++) {
        const scene = scenes[i];
        onProgress?.(i + 1, scenes.length, `Generating image ${i + 1}/${scenes.length}...`);

        try {
            // Generate with Puter
            const base64 = await generateImageWithPuter(scene.prompt);

            // Upload to Firebase
            onProgress?.(i + 1, scenes.length, `Uploading image ${i + 1}/${scenes.length}...`);
            const firebaseUrl = await uploadImageToFirebase(base64, sessionId, i);

            imageUrls.push(firebaseUrl);
        } catch (error) {
            console.error(`Failed to generate scene ${i}:`, error);
            // Use a placeholder or retry
            imageUrls.push(''); // Will be handled by backend
        }
    }

    return imageUrls;
}
