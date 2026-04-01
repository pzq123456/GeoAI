import { reactive, markRaw } from 'vue';

export interface LayerOptions {
    opacity?: number;
    visible?: boolean;
    props?: Record<string, any>;
    data?: any;
}

export interface LayerType {
    layerName: string;
    [key: string]: any;
}

export class Layer {
    public id: string;
    public type: LayerType;
    public typeName: string;
    public state: {
        opacity: number;
        visible: boolean;
        getFillColor?: any;
        getLineColor?: any;
        [key: string]: any;
    };
    public data: any;

    constructor(id: string, type: LayerType, options: LayerOptions = {}) {
        this.id = id;
        this.type = markRaw(type);
        this.typeName = this.type.layerName;

        this.state = reactive({
            opacity: options.opacity ?? 1,
            visible: options.visible ?? true,
            ...options.props
        });

        this.data = options.data ? markRaw(options.data) : null;
    }

    get getFillColor(): any {
        return this.state.getFillColor;
    }

    set getFillColor(value: any) {
        this.state.getFillColor = value;
    }

    get getLineColor(): any {
        return this.state.getLineColor;
    }

    set getLineColor(value: any) {
        this.state.getLineColor = value;
    }

    get opacity(): number {
        return this.state.opacity;
    }

    set opacity(value: number) {
        this.state.opacity = value;
    }

    get visible(): boolean {
        return this.state.visible;
    }

    set visible(value: boolean) {
        this.state.visible = value;
    }
}
