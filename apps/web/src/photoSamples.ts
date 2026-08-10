import crownRoyalBackUrl from '../../../fixtures/demo/samples/crown-royal/back.jpg?url'
import crownRoyalFrontUrl from '../../../fixtures/demo/samples/crown-royal/front.jpg?url'
import darkArtsBackUrl from '../../../fixtures/demo/samples/dark-arts/back.jpg?url'
import darkArtsFrontUrl from '../../../fixtures/demo/samples/dark-arts/front.jpg?url'
import muralistBackUrl from '../../../fixtures/demo/samples/muralist/back.jpg?url'
import muralistFrontUrl from '../../../fixtures/demo/samples/muralist/front.jpg?url'
import muralistInsideUrl from '../../../fixtures/demo/samples/muralist/inside.jpg?url'
import turtleRabbitBackUrl from '../../../fixtures/demo/samples/turtle-rabbit/back.jpg?url'
import turtleRabbitFrontUrl from '../../../fixtures/demo/samples/turtle-rabbit/front.jpg?url'
import sevenFathomsBackUrl from '../../../fixtures/demo/seven-fathoms-back.jpg?url'
import sevenFathomsFrontUrl from '../../../fixtures/demo/seven-fathoms-front.jpg?url'

interface SampleAsset {
  url: string
  filename: string
  mediaType: 'image/jpeg' | 'image/png'
}

export interface SamplePhotoSet {
  id: string
  name: string
  description: string
  photoCount: number
}

interface SamplePhotoDefinition extends SamplePhotoSet {
  assets: SampleAsset[]
}

const jpeg = (url: string, filename: string): SampleAsset => ({
  url,
  filename,
  mediaType: 'image/jpeg',
})

const SAMPLE_DEFINITIONS: SamplePhotoDefinition[] = [
  {
    id: 'seven-fathoms',
    name: 'Seven Fathoms',
    description: 'Premium rum',
    photoCount: 2,
    assets: [
      jpeg(sevenFathomsFrontUrl, 'seven-fathoms-front.jpg'),
      jpeg(sevenFathomsBackUrl, 'seven-fathoms-back.jpg'),
    ],
  },
  {
    id: 'turtle-rabbit',
    name: 'Turtle Rabbit',
    description: 'Tequila',
    photoCount: 2,
    assets: [
      jpeg(turtleRabbitFrontUrl, 'turtle-rabbit-front.jpg'),
      jpeg(turtleRabbitBackUrl, 'turtle-rabbit-back.jpg'),
    ],
  },
  {
    id: 'dark-arts',
    name: 'Dark Arts Whiskey House',
    description: 'Straight bourbon whisky',
    photoCount: 2,
    assets: [
      jpeg(darkArtsFrontUrl, 'dark-arts-front.jpg'),
      jpeg(darkArtsBackUrl, 'dark-arts-back.jpg'),
    ],
  },
  {
    id: 'muralist',
    name: 'Muralist',
    description: 'Straight bourbon whisky',
    photoCount: 3,
    assets: [
      jpeg(muralistFrontUrl, 'muralist-front.jpg'),
      jpeg(muralistInsideUrl, 'muralist-inside.jpg'),
      jpeg(muralistBackUrl, 'muralist-back.jpg'),
    ],
  },
  {
    id: 'crown-royal',
    name: 'Crown Royal',
    description: 'Canadian whisky',
    photoCount: 2,
    assets: [
      jpeg(crownRoyalFrontUrl, 'crown-royal-front.jpg'),
      jpeg(crownRoyalBackUrl, 'crown-royal-back.jpg'),
    ],
  },
]

export const SAMPLE_PHOTO_SETS: SamplePhotoSet[] = SAMPLE_DEFINITIONS.map(
  ({ id, name, description, photoCount }) => ({ id, name, description, photoCount }),
)

export async function loadSamplePhotos(sampleId: string): Promise<File[]> {
  const sample = SAMPLE_DEFINITIONS.find(({ id }) => id === sampleId)
  if (!sample) throw new Error('That sample label is unavailable.')

  return Promise.all(sample.assets.map(async (asset) => {
    const response = await fetch(asset.url)
    if (!response.ok) throw new Error('The sample photos could not be loaded.')
    return new File([await response.arrayBuffer()], asset.filename, { type: asset.mediaType })
  }))
}
