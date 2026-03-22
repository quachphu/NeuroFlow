import { useRef, useState } from 'react';
import { Upload, X, Mic, Square } from 'lucide-react';

export default function AudioUpload({ onUpload, onClose }) {
  const fileRef = useRef(null);
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  function handleFile(file) {
    if (file && (file.type.startsWith('audio/') || file.name.match(/\.(wav|mp3|m4a|webm|ogg)$/i))) {
      onUpload(file);
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/webm' });
        const file = new File([blob], `recording_${Date.now()}.webm`, { type: 'audio/webm' });
        stream.getTracks().forEach((t) => t.stop());
        onUpload(file);
      };

      recorder.start();
      setMediaRecorder(recorder);
      setRecording(true);
    } catch {
      alert('Could not access microphone');
    }
  }

  function stopRecording() {
    mediaRecorder?.stop();
    setRecording(false);
    setMediaRecorder(null);
  }

  return (
    <div className="px-4 pb-2 animate-fade-in">
      <div
        className={`
          relative border-2 border-dashed rounded-2xl p-6 text-center transition-colors
          ${dragOver ? 'border-blue bg-blue/5' : 'border-border bg-white'}
        `}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <button
          onClick={onClose}
          className="absolute top-3 right-3 p-1 rounded-lg hover:bg-cream transition-colors text-text-muted"
        >
          <X size={16} />
        </button>

        <div className="space-y-3">
          <div className="flex justify-center gap-3">
            <button
              onClick={() => fileRef.current?.click()}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cream hover:bg-cream-dark transition-colors text-sm font-medium"
            >
              <Upload size={16} />
              Upload file
            </button>
            <button
              onClick={recording ? stopRecording : startRecording}
              className={`
                flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors
                ${recording
                  ? 'bg-red-50 text-red-500 hover:bg-red-100'
                  : 'bg-sage/10 text-sage hover:bg-sage/20'
                }
              `}
            >
              {recording ? <><Square size={14} /> Stop</> : <><Mic size={16} /> Record</>}
            </button>
          </div>
          <p className="text-xs text-text-muted">
            {recording
              ? 'Recording... click Stop when done'
              : 'Drag & drop audio, upload a file, or record directly'
            }
          </p>
        </div>

        <input
          ref={fileRef}
          type="file"
          accept="audio/*"
          className="hidden"
          onChange={(e) => handleFile(e.target.files[0])}
        />
      </div>
    </div>
  );
}
