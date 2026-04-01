// 用于管理图层的 deck.gl 对象
import {MapboxOverlay} from '@deck.gl/mapbox';

export function useDeckOverlay(map) {
    const DeckOverlay = new MapboxOverlay({
        interleaved: true, 
        layers: [], // layers
        interleaved: true, // 确保 DeckGL 层渲染在 Mapbox 上层
    });

    if(map) {
        map.addControl(DeckOverlay);
    }
    
    return DeckOverlay;
}