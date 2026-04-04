/**
 * Generate voiceover audio files using ElevenLabs TTS API.
 * Reads script from voiceover-script.json, outputs MP3 files to public/walkthrough/audio/
 */
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCRIPT = JSON.parse(readFileSync(resolve(__dirname, 'voiceover-script.json'), 'utf-8'));
const OUT_DIR = resolve(__dirname, '../public/walkthrough/audio');
mkdirSync(OUT_DIR, { recursive: true });

// ElevenLabs config
const API_KEY = process.env.ELEVENLABS_API_KEY;
if (!API_KEY) {
  console.error('Missing ELEVENLABS_API_KEY environment variable');
  process.exit(1);
}

// Use "Adam" voice (clear, professional male) - or change voice_id
const VOICE_ID = 'onwK4e9ZLuTAKqWW03F9'; // Daniel - Steady Broadcaster
const MODEL_ID = 'eleven_multilingual_v2';

async function generateAudio(text, outputPath) {
  const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}`, {
    method: 'POST',
    headers: {
      'xi-api-key': API_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      model_id: MODEL_ID,
      voice_settings: {
        stability: 0.65,
        similarity_boost: 0.75,
        style: 0.3,
        use_speaker_boost: true,
      },
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`ElevenLabs API error ${response.status}: ${err}`);
  }

  const buffer = Buffer.from(await response.arrayBuffer());
  writeFileSync(outputPath, buffer);
  return buffer.length;
}

async function main() {
  console.log(`Generating ${SCRIPT.length} voiceover segments...`);

  for (let i = 0; i < SCRIPT.length; i++) {
    const segment = SCRIPT[i];
    const filename = `${String(i).padStart(2, '0')}-${segment.scene}.mp3`;
    const outputPath = resolve(OUT_DIR, filename);

    console.log(`[${i + 1}/${SCRIPT.length}] ${segment.scene}: "${segment.text.substring(0, 50)}..."`);

    const bytes = await generateAudio(segment.text, outputPath);
    console.log(`  -> Saved ${filename} (${(bytes / 1024).toFixed(1)} KB)`);

    // Small delay to avoid rate limiting
    await new Promise(r => setTimeout(r, 500));
  }

  console.log(`\nDone! Audio files saved to: ${OUT_DIR}`);
}

main().catch(console.error);
