# Font licenses

All bundled fonts are free to use in videos and to redistribute under their own licenses.

| file | family | license |
|---|---|---|
| TikTokSans-ExtraBold.ttf, TikTokSans-SemiBold.ttf | TikTok Sans (TikTok) | SIL Open Font License 1.1 |
| Montserrat-Black.ttf, Montserrat-Bold.ttf | Montserrat (Julieta Ulanovsky) | SIL OFL 1.1 |
| Poppins-ExtraBold.ttf | Poppins (Indian Type Foundry) | SIL OFL 1.1 |
| Anton-Regular.ttf | Anton (Vernon Adams) | SIL OFL 1.1 |
| Bangers-Regular.ttf | Bangers (Vernon Adams) | SIL OFL 1.1 |
| BebasNeue-Regular.ttf | Bebas Neue (Dharma Type) | SIL OFL 1.1 |
| JetBrainsMono-ExtraBold.ttf | JetBrains Mono (JetBrains) | SIL OFL 1.1 |
| LuckiestGuy-Regular.ttf | Luckiest Guy (Astigmatic) | Apache License 2.0 |
| Fredoka-Bold.ttf | Fredoka (Milena Brandao, Hafontia) | SIL OFL 1.1 |
| Nunito-ExtraBold.ttf | Nunito (Vernon Adams, Cyreal, Jacques Le Bailly) | SIL OFL 1.1 |
| PermanentMarker-Regular.ttf | Permanent Marker (Font Diner) | Apache License 2.0 |
| Inter-SemiBold.ttf, Inter-ExtraBold.ttf | Inter (Rasmus Andersson) | SIL OFL 1.1 |
| Manrope-ExtraBold.ttf | Manrope (Mikhail Sharanda) | SIL OFL 1.1 |
| SpaceGrotesk-Bold.ttf | Space Grotesk (Florian Karsten) | SIL OFL 1.1 |
| InstrumentSerif-Regular.ttf | Instrument Serif (Rodrigo Fuenzalida, Instrument) | SIL OFL 1.1 |
| ArchivoBlack-Regular.ttf | Archivo Black (Hector Gatti, Omnibus-Type) | SIL OFL 1.1 |
| Oswald-SemiBold.ttf | Oswald (Vernon Adams, Kalapi Gajjar, Cyreal) | SIL OFL 1.1 |
| LilitaOne-Regular.ttf | Lilita One (Juan Montoreano) | SIL OFL 1.1 |
| TitanOne-Regular.ttf | Titan One (Rodrigo Fuenzalida) | SIL OFL 1.1 |
| PressStart2P-Regular.ttf | Press Start 2P (CodeMan38) | SIL OFL 1.1 |
| Caveat-Bold.ttf | Caveat (Pablo Impallari) | SIL OFL 1.1 |
| BricolageGrotesque-ExtraBold.ttf | Bricolage Grotesque (Mathieu Triay) | SIL OFL 1.1 |

Inter, Manrope, Space Grotesk, Oswald, Caveat and Bricolage Grotesque are static instances (one weight each) cut from the Google Fonts variable fonts with fontTools, renamed so libass can select them by family name ("Inter SemiBold"), and, like the static ones added with them, subset to Latin, Latin Extended, Greek, Cyrillic and common punctuation to keep them small. They keep the OFL.

Fredoka and Nunito are static instances (Bold 700, ExtraBold 800) cut from the variable fonts and renamed so libass can pick them by name. Montserrat, TikTok Sans and Poppins had their internal family names adjusted (e.g. "Montserrat Black") so libass can select each weight by name. Under the OFL that makes them modified versions; they keep the original license.
