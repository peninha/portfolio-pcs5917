"""Extração para o classificador, com os mesmos cálculos do notebook exploratório.

Não aprende parâmetros a partir dos dados e não usa rótulos nem metadados.
"""

from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


def extrair_arquivo(path: Path, config: dict) -> dict[str, float]:
    y, sr = sf.read(path, dtype='float32', always_2d=True)
    if len(y) == 0 or not np.isfinite(y).all():
        raise ValueError(f'Áudio vazio ou com valores inválidos: {path.name}')
    y = y.mean(axis=1)
    if sr != config['sr']:
        y = librosa.resample(y, orig_sr=sr, target_sr=config['sr'])
    sr = config['sr']
    features = {
        'duration_s': len(y) / sr,
        'peak': float(np.max(np.abs(y))),
        'rms_global': float(np.sqrt(np.mean(y.astype('float64') ** 2))),
        'near_clip_fraction': float(np.mean(np.abs(y) >= 0.999)),
    }
    n_fft, hop = config['n_fft'], config['hop_length']
    magnitude = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    mel = librosa.feature.melspectrogram(
        S=magnitude**2, sr=sr, n_mels=config['n_mels'])
    mfcc = librosa.feature.mfcc(
        S=librosa.power_to_db(mel), n_mfcc=config['n_mfcc'])
    rms = librosa.feature.rms(y=y, frame_length=n_fft, hop_length=hop)
    sequences = {
        'rms': rms,
        'zcr': librosa.feature.zero_crossing_rate(y, frame_length=n_fft, hop_length=hop),
        'centroid_hz': librosa.feature.spectral_centroid(S=magnitude, sr=sr),
        'bandwidth_hz': librosa.feature.spectral_bandwidth(S=magnitude, sr=sr),
        'rolloff_hz': librosa.feature.spectral_rolloff(S=magnitude, sr=sr, roll_percent=.85),
        'flatness': librosa.feature.spectral_flatness(S=magnitude),
    }
    for name, values in sequences.items():
        features[f'{name}_mean'] = float(values.mean())
        features[f'{name}_std'] = float(values.std(ddof=0))
    for i, values in enumerate(mfcc, start=1):
        features[f'mfcc_{i:02d}_mean'] = float(values.mean())
        features[f'mfcc_{i:02d}_std'] = float(values.std(ddof=0))
    features['low_energy_fraction'] = float(
        np.mean(rms < 10 ** (config['silence_dbfs'] / 20)))
    if not all(np.isfinite(v) for v in features.values()):
        raise ValueError(f'Atributos inválidos: {path.name}')
    return features
