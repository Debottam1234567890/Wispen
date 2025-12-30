/**
 * Puter Image Generator via Puppeteer - DEBUG VERSION
 * Runs in headed mode to see what's happening
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function generateImage(prompt, outputPath) {
    console.log('Launching browser (headed for debugging)...');
    const browser = await puppeteer.launch({
        headless: false, // Visible browser for debugging
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        protocolTimeout: 180000
    });

    try {
        const page = await browser.newPage();
        page.setDefaultTimeout(120000);

        // Listen for console logs from the page
        page.on('console', msg => console.log('PAGE LOG:', msg.text()));

        const html = `
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://js.puter.com/v2/"></script>
        </head>
        <body>
            <h1>Puter Image Generation Test</h1>
            <div id="status">Loading Puter.js...</div>
            <div id="result"></div>
            <script>
                window.imageReady = false;
                window.imageData = null;
                window.imageError = null;
                
                console.log('Script loaded, checking puter...');
                
                // Check if puter loads
                const checkPuter = setInterval(() => {
                    if (typeof puter !== 'undefined') {
                        console.log('Puter object found:', Object.keys(puter));
                        if (puter.ai) {
                            console.log('puter.ai available');
                            clearInterval(checkPuter);
                        }
                    }
                }, 500);
                
                window.startGeneration = async function(prompt) {
                    console.log('Starting generation with prompt:', prompt);
                    document.getElementById('status').innerText = 'Generating...';
                    try {
                        console.log('Calling puter.ai.txt2img...');
                        const img = await puter.ai.txt2img(prompt, { 
                            model: "black-forest-labs/FLUX.1-schnell"
                        });
                        console.log('Got image:', typeof img, img);
                        window.imageData = img.src;
                        window.imageReady = true;
                        document.getElementById('status').innerText = 'Done!';
                        document.getElementById('result').appendChild(img);
                    } catch (error) {
                        console.error('Generation error:', error);
                        window.imageError = error.message || String(error);
                        window.imageReady = true;
                        document.getElementById('status').innerText = 'Error: ' + window.imageError;
                    }
                };
            </script>
        </body>
        </html>
        `;

        await page.setContent(html);

        console.log('Waiting for Puter to load...');
        await page.waitForFunction(() => typeof puter !== 'undefined' && puter.ai, {
            timeout: 30000
        });

        console.log('Puter loaded, starting generation...');
        await page.evaluate((p) => window.startGeneration(p), prompt);

        console.log('Waiting for image generation (you may see a login popup)...');

        // Wait longer and check manually
        for (let i = 0; i < 60; i++) {
            await new Promise(r => setTimeout(r, 2000));
            const status = await page.evaluate(() => ({
                ready: window.imageReady,
                error: window.imageError,
                hasData: !!window.imageData
            }));
            console.log(`Check ${i + 1}/60:`, status);
            if (status.ready) break;
        }

        const result = await page.evaluate(() => ({
            error: window.imageError,
            data: window.imageData
        }));

        if (result.error) {
            throw new Error(result.error);
        }

        if (!result.data) {
            throw new Error('No image data returned');
        }

        console.log('Image received, saving...');

        let imageData;
        if (result.data.startsWith('data:image')) {
            const base64Data = result.data.replace(/^data:image\/\w+;base64,/, '');
            imageData = Buffer.from(base64Data, 'base64');
        } else if (result.data.startsWith('http')) {
            const response = await page.goto(result.data, { waitUntil: 'networkidle0' });
            imageData = await response.buffer();
        } else {
            throw new Error('Unknown image format');
        }

        const outputDir = path.dirname(outputPath);
        if (outputDir && !fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir, { recursive: true });
        }

        fs.writeFileSync(outputPath, imageData);
        console.log('SUCCESS: Image saved to:', outputPath);
        return true;

    } catch (error) {
        console.error('ERROR:', error.message);
        return false;
    } finally {
        // Keep browser open for debugging
        console.log('Keeping browser open for 30 seconds for inspection...');
        await new Promise(r => setTimeout(r, 30000));
        await browser.close();
    }
}

const args = process.argv.slice(2);
if (args.length < 2) {
    console.log('Usage: node generate_image_puter_debug.cjs "prompt" "output_path.png"');
    process.exit(1);
}

generateImage(args[0], args[1])
    .then(success => process.exit(success ? 0 : 1))
    .catch(err => {
        console.error(err);
        process.exit(1);
    });
