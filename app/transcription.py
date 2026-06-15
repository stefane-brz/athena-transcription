import numpy as np
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio

def transcript(chemin_audio, mode="small", device="cpu", compute_type="int8"):
    """
    Transcription classique d'un coup (Optimisée vitesse : beam_size=1, vad_filter=True).
    """
    model = WhisperModel(mode, device=device, compute_type=compute_type)
    print(f"Modèle chargé ! Traitement de l'audio entier : {chemin_audio}...")

    # On lance la transcription avec vad_filter=True et beam_size=1 pour plus de rapidité
    segments, info = model.transcribe(chemin_audio, beam_size=1, language="fr", vad_filter=True)

    texte_transcrit = ""
    for segment in segments:
        texte_transcrit += segment.text + " "

    print("Transcription finie")
    return texte_transcrit


def transcript_generator(chemin_audio, mode="small", device="cpu", compute_type="int8", chunk_size_seconds=300):
    """
    Générateur qui charge l'audio, le découpe par tranches de N secondes,
    et produit les transcriptions au fur et à mesure.
    """
    model = WhisperModel(mode, device=device, compute_type=compute_type)
    print(f"Modèle chargé ! Découpage et traitement de l'audio : {chemin_audio}...")

    # Charger l'audio complet sous forme de tableau numpy float32 à 16kHz
    audio_data = decode_audio(chemin_audio, sampling_rate=16000)
    total_samples = len(audio_data)
    chunk_size_samples = chunk_size_seconds * 16000
    
    total_chunks = int(np.ceil(total_samples / chunk_size_samples))
    if total_chunks == 0:
        total_chunks = 1

    for idx in range(total_chunks):
        start_sample = idx * chunk_size_samples
        end_sample = min((idx + 1) * chunk_size_samples, total_samples)
        
        # Extraire la tranche de données audio
        audio_chunk = audio_data[start_sample:end_sample]
        
        if len(audio_chunk) == 0:
            continue
            
        print(f"Transcription de la tranche {idx + 1}/{total_chunks}...")
        
        # Transcrire la tranche (beam_size=1 et vad_filter=True pour une vitesse maximale)
        segments, info = model.transcribe(audio_chunk, beam_size=1, language="fr", vad_filter=True)
        
        texte_chunk = ""
        for segment in segments:
            texte_chunk += segment.text + " "
            
        yield idx + 1, total_chunks, texte_chunk