import { useCallback, useMemo, useRef, useState } from 'react';
import type { ClipboardEvent, KeyboardEvent } from 'react';
import {
  Badge, Breadcrumb, BreadcrumbButton, BreadcrumbDivider, BreadcrumbItem,
  Button, Checkbox, Divider, DrawerBody, DrawerFooter, DrawerHeader,
  DrawerHeaderTitle, Field, FluentProvider, InlineDrawer, Input,
  MessageBar, MessageBarBody, MessageBarTitle, Radio, RadioGroup,
  Select, Spinner, Tab, TabList, Table, TableBody, TableCell,
  TableHeader, TableHeaderCell, TableRow, Textarea, Tooltip,
  webLightTheme,
} from '@fluentui/react-components';
import {
  ArrowLeft20Regular, ArrowRight20Regular, CheckmarkCircle20Regular,
  ChevronLeft20Regular, ChevronRight20Regular, Database20Regular,
  Dismiss20Regular, DocumentTable20Regular, Home20Regular,
  Info20Regular, PanelRight20Regular, Search20Regular,
  Warning20Regular,
} from '@fluentui/react-icons';
import {
  amount, classifyIdentityChange, extractLinks, nextViewed,
  previewTotal, suggestedPrice, warnings,
} from './logic.mjs';
import type { EvidenceImage } from './logic.mjs';

type Origin = 'auto' | 'similar' | 'manual' | 'none';
type Route = 'workbench' | 'summary';
type KnowledgeDecision = 'correct' | 'new' | 'case' | '';
type DetailTab = 'price' | 'specs' | 'history';

type Source = {
  id: string;
  name: string;
  type: string;
  price: number | null;
  surveyedAt: string;
  vat: string;
  transport: string;
  links: string[];
  images: EvidenceImage[];
  explanation: string;
  isPrimary: boolean;
};
type Asset = {
  id: string;
  name: string;
  originalSpecs: string;
  specs: string;
  unit: string;
  qty: number;
  originalQty: number;
  customerPrice: number | null;
  survey: number | null;
  transportPercent: number | null;
  proposed: number | null;
  manualPrice: boolean;
  match: 'high' | 'similar' | 'none' | 'manual';
  origin: Origin;
  sources: Source[];
  viewed: boolean;
  needsRecheck: boolean;
  resolution: KnowledgeDecision;
  note: string;
  activity: string[];
};

type Similar = { id: string; name: string; similarity: string; differences: string; survey: number; source: Source };

const vnd = (price: number | null | undefined) =>
  price === null || price === undefined ? '—' : new Intl.NumberFormat('vi-VN').format(price);

const exampleSource = (id: string, name: string, price: number | null, type = 'Giá khảo sát Internet'): Source => ({
  id, name, price, type, surveyedAt: '10/2026', vat: 'Chưa bao gồm VAT',
  transport: 'Chưa bao gồm vận chuyển',
  links: [`https://example.com/valora-demo/${id.toLowerCase()}`], images: [],
  explanation: 'Dữ liệu minh họa phục vụ thử nghiệm UI, không phải giá khảo sát thực tế.', isPrimary: true,
});

const initial: Asset[] = [
  {
    id:'TS-001',name:'Máy tiện CNC',originalSpecs:'Model X100 · Công suất 15 kW · Mới 100%',
    specs:'Model X100 · Công suất 15 kW · Mới 100%',unit:'cái',qty:2,originalQty:2,
    customerPrice:110000000,survey:100000000,transportPercent:5,proposed:105000000,
    manualPrice:false,match:'high',origin:'auto',viewed:false,needsRecheck:false,resolution:'',
    sources:[exampleSource('NG-A01','Khảo sát Internet — nguồn A',100000000),{
      ...exampleSource('NG-A02','Khảo sát Internet — nguồn B',145000000),isPrimary:false,
    }],note:'Tham chiếu nguồn A; giá nguồn B có chênh lệch, cần nhân viên xem xét.',activity:['VALORA tự điền từ nguồn đã đối chiếu (minh họa)'],
  },
  {
    id:'TS-002',name:'Máy nén khí trục vít',originalSpecs:'Công suất 22 kW · Chưa rõ model',
    specs:'Công suất 22 kW · Chưa rõ model',unit:'bộ',qty:1,originalQty:1,
    customerPrice:null,survey:null,transportPercent:null,proposed:null,manualPrice:false,
    match:'similar',origin:'similar',viewed:false,needsRecheck:false,resolution:'',
    sources:[],note:'',activity:['Chưa có nguồn đáp ứng điều kiện tự điền'],
  },
  {
    id:'TS-003',name:'Máy phát điện',originalSpecs:'Model G100 · Công suất 100 kVA · Đã sử dụng',
    specs:'Model G100 · Công suất 100 kVA · Đã sử dụng',unit:'cái',qty:3,originalQty:3,
    customerPrice:85000000,survey:76000000,transportPercent:5,proposed:80000000,manualPrice:true,
    match:'high',origin:'auto',viewed:false,needsRecheck:false,resolution:'',
    sources:[exampleSource('NG-C01','Khảo sát Internet — máy phát điện G100',76000000)],note:'Giá do nhân viên quyết định, không ràng buộc công thức.',activity:['VALORA tự điền nguồn; nhân viên giữ quyền quyết định giá'],
  },
  {
    id:'TS-004',name:'Máy cắt laser',originalSpecs:'Công suất 3 kW · Chưa rõ model',
    specs:'Công suất 3 kW · Chưa rõ model',unit:'cái',qty:1,originalQty:1,
    customerPrice:null,survey:null,transportPercent:null,proposed:null,manualPrice:false,
    match:'none',origin:'none',viewed:false,needsRecheck:false,resolution:'',sources:[],note:'',
    activity:['Không tìm thấy nguồn phù hợp từ Kho tri thức'],
  },
  {
    id:'TS-005',name:'Hệ thống bơm công nghiệp',originalSpecs:'Công suất 11 kW · Bộ điều khiển tích hợp',
    specs:'Công suất 11 kW · Bộ điều khiển tích hợp',unit:'bộ',qty:2,originalQty:2,
    customerPrice:35000000,survey:31000000,transportPercent:4,proposed:32240000,manualPrice:false,
    match:'high',origin:'auto',viewed:false,needsRecheck:false,resolution:'',
    sources:[exampleSource('NG-E01','Thuyết minh đơn giá — Bơm công nghiệp',31000000,'Thuyết minh đơn giá')],
    note:'',activity:['Đối chiếu model và điều kiện giá (minh họa)'],
  },
  {
    id:'TS-006',name:'Máy ép thủy lực',originalSpecs:'Lực ép 100 tấn · Đã sử dụng',
    specs:'Lực ép 100 tấn · Đã sử dụng',unit:'cái',qty:1,originalQty:1,
    customerPrice:95000000,survey:88000000,transportPercent:null,proposed:null,manualPrice:false,
    match:'high',origin:'auto',viewed:false,needsRecheck:true,resolution:'',
    sources:[exampleSource('NG-F01','Khảo sát Internet — máy ép thủy lực',88000000)],
    note:'Chưa xác định điều kiện vận chuyển; không tự coi chi phí bằng 0.',activity:['Chưa đủ điều kiện tính đơn giá đề xuất tự động'],
  },
];

const similar: Similar[] = [
  { id:'KT-082',name:'Máy nén khí trục vít 22 kW — K22',similarity:'Cùng công suất, có model',
    differences:'Khác xuất xứ và điều kiện giao hàng; cần kiểm tra',survey:42000000,
    source:exampleSource('NG-S82','Giá tham khảo — máy nén khí K22',42000000) },
  { id:'KT-109',name:'Máy nén khí trục vít 22 kW — C22',similarity:'Cùng công suất và chủng loại',
    differences:'Khác hãng, cấu hình bộ lọc; không đồng nhất tài sản',survey:47000000,
    source:exampleSource('NG-S109','Giá tham khảo — máy nén khí C22',47000000) },
];

function statusText(a: Asset) {
  if (a.needsRecheck) return 'Cần kiểm tra';
  if (a.proposed === null) return 'Thiếu đơn giá';
  if (a.manualPrice) return 'Đã điều chỉnh';
  if (a.origin === 'auto') return 'Tự điền';
  return 'Đã bổ sung';
}

function Status({asset}: {asset: Asset}) {
  const color = asset.needsRecheck || asset.proposed === null ? 'warning' : asset.origin === 'auto' && !asset.manualPrice ? 'success' : 'informative';
  return <Badge size="small" appearance="tint" color={color}>{statusText(asset)}</Badge>;
}

function SourceCard({source,onPrefer}: {source: Source; onPrefer?:()=>void}) {
  return <article className="source-card" aria-label={`Nguồn ${source.name}`}>
    <div className="source-head">
      <div><div className="source-title">{source.name}</div><span className="muted tiny">{source.type} · {source.surveyedAt}</span></div>
      {source.isPrimary && <Badge appearance="tint" color="success" size="small">Nguồn ưu tiên</Badge>}
    </div>
    <div className="source-price">{source.price===null?'Chưa xác định':vnd(source.price)} <span className="muted">đ / đơn vị</span></div>
    <div className="source-conditions">{source.vat} · {source.transport}</div>
    <div className="source-links">{source.links.map((link,i)=><a href={link} target="_blank" rel="noopener noreferrer" key={link+i}>{link}</a>)}</div>
    {source.images.map(img=><figure className="image-preview" key={img.id}><img src={img.dataUrl} alt={`Ảnh chứng cứ ${img.name}`}/><figcaption>{img.name}</figcaption></figure>)}
    <p className="muted tiny">{source.explanation}</p>
    {!source.isPrimary&&onPrefer&&<Button size="small" appearance="secondary" onClick={onPrefer}>Chọn nguồn ưu tiên</Button>}
  </article>;
}

function SideNav({collapsed,onToggle,onShowSummary,onShowWorkbench,route}: {
  collapsed:boolean;onToggle:()=>void;onShowSummary:()=>void;onShowWorkbench:()=>void;route:Route;
}) {
  return <aside className={`sidebar ${collapsed?'collapsed':''}`} aria-label="Điều hướng VALORA">
    <div className="brand"><span className="brand-symbol">V</span>{!collapsed&&<span><strong>VALORA</strong><small>Thẩm định máy móc thiết bị</small></span>}</div>
    <nav className="nav-block" aria-label="Điều hướng chính">
      {!collapsed&&<div className="nav-heading">KHÔNG GIAN LÀM VIỆC</div>}
      <Tooltip content="Trang chủ (minh họa)" relationship="label"><Button appearance="subtle" icon={<Home20Regular/>} className="side-btn" disabled={!collapsed}>{!collapsed?'Trang chủ':''}</Button></Tooltip>
      <Tooltip content="Phân tích danh mục" relationship="label"><Button appearance={route==='workbench'?'secondary':'subtle'} icon={<DocumentTable20Regular/>} className={`side-btn ${route==='workbench'?'nav-selected':''}`} onClick={onShowWorkbench}>{collapsed?'':'Phân tích danh mục'}</Button></Tooltip>
      <Tooltip content="Tổng kết & phiên bản" relationship="label"><Button appearance={route==='summary'?'secondary':'subtle'} icon={<CheckmarkCircle20Regular/>} className={`side-btn ${route==='summary'?'nav-selected':''}`} onClick={onShowSummary}>{collapsed?'':'Tổng kết & phiên bản'}</Button></Tooltip>
      {!collapsed&&<div className="nav-heading second">DỮ LIỆU THAM KHẢO</div>}
      <Tooltip content="Kho tri thức: minh họa" relationship="label"><Button appearance="subtle" icon={<Database20Regular/>} className="side-btn" disabled>{collapsed?'':'Quản lý Kho tri thức'}</Button></Tooltip>
    </nav>
    <div className="sidebar-bottom">
      <Tooltip content={collapsed?'Mở rộng thanh điều hướng':'Thu gọn thanh điều hướng'} relationship="label"><Button size="small" appearance="subtle" icon={<PanelRight20Regular/>} onClick={onToggle}>{collapsed?'':'Thu gọn'}</Button></Tooltip>
      {!collapsed&&<span className="tiny muted">Prototype Fluent UI v9 · v02</span>}
    </div>
  </aside>;
}

export default function App() {
  const [assets,setAssets] = useState<Asset[]>(initial);
  const [selectedId,setSelectedId] = useState('TS-001');
  const [isDrawerOpen,setDrawerOpen] = useState(true);
  const [route,setRoute] = useState<Route>('workbench');
  const [navCollapsed,setNavCollapsed] = useState(false);
  const [filter,setFilter] = useState('all');
  const [search,setSearch] = useState('');
  const [detailTab,setDetailTab] = useState<DetailTab>('price');
  const [similarSearch,setSimilarSearch] = useState('');
  const [draftNote,setDraftNote] = useState<string|null>(null);
  const [draftTransport,setDraftTransport] = useState<string|null>(null);
  const [draftSurvey,setDraftSurvey] = useState<string|null>(null);
  const [draftProposed,setDraftProposed] = useState<string|null>(null);
  const [identityDraft,setIdentityDraft] = useState<string|null>(null);
  const [identityClass,setIdentityClass] = useState<KnowledgeDecision>('');
  const [exportedVersion,setExportedVersion] = useState(0);
  const [exportSignature,setExportSignature] = useState('');
  const [ack,setAck] = useState(false);
  const [workRevision,setWorkRevision] = useState(0);
  const [notice,setNotice] = useState('Dữ liệu minh họa; không kết nối máy chủ VALORA.');
  const topScrollbar=useRef<HTMLDivElement>(null);
  const tableScrollbar=useRef<HTMLDivElement>(null);
  const syncing=useRef(false);
  const titleRef=useRef<HTMLHeadingElement>(null);

  const selected=assets.find(a=>a.id===selectedId) ?? assets[0];
  const selectedIndex=assets.findIndex(a=>a.id===selected.id);
  const summary=warnings(assets);
  const total=previewTotal(assets);
  const currentSignature=`${workRevision}`;
  const changedSinceExport=exportedVersion>0 && exportSignature!==currentSignature;
  const emitChange=useCallback((message:string)=>{setWorkRevision(n=>n+1);setNotice(`${message} · Chỉ lưu trong phiên prototype.`);},[]);
  const patch=useCallback((id:string,fn:(a:Asset)=>Asset,message:string)=>{
    setAssets(old=>old.map(a=>a.id===id?fn(a):a));emitChange(message);
  },[emitChange]);

  const gotoAsset=useCallback((id:string)=>{
    if(id!==selectedId){setAssets(prev=>nextViewed(prev,selectedId));setSelectedId(id);}
    setDetailTab('price');setDrawerOpen(true);setDraftNote(null);setDraftTransport(null);setDraftSurvey(null);setDraftProposed(null);setIdentityDraft(null);setNotice('Đang xem tài sản '+id+'; chưa chấp nhận làm cơ sở thẩm định.');
  },[selectedId]);
  const gotoByOffset=(diff:number)=>{
    const next=assets[selectedIndex+diff];if(next)gotoAsset(next.id);
  };
  const switchRoute=(next:Route)=>{
    if(next==='summary'&&route!=='summary')setAssets(prev=>nextViewed(prev,selectedId));
    setRoute(next);setAck(false);requestAnimationFrame(()=>titleRef.current?.focus());
  };
  const visible=useMemo(()=>assets.filter(a=>{
    const q=search.toLocaleLowerCase('vi').trim();
    const matches=!q||[a.id,a.name,a.specs].some(x=>x.toLocaleLowerCase('vi').includes(q));
    return matches&&(filter==='all'||filter==='unviewed'&&!a.viewed||filter==='missing'&&a.proposed===null||filter==='recheck'&&a.needsRecheck);
  }),[assets,search,filter]);

  const rowDisplayLink=(id:string)=>{
    setFilter('all');setSearch('');gotoAsset(id);setRoute('workbench');
  };
  const clearNotice=()=>setNotice('');

  const changeField=(key:'qty'|'proposed',raw:string)=>{
    const n=raw.trim()===''?null:Number(raw);
    if(n!==null&&(!Number.isFinite(n)||n<0))return;
    if(key==='qty') {
      if(n===null||!Number.isInteger(n))return;
      patch(selected.id,a=>({...a,qty:n,activity:[`SL nguồn đổi ${a.qty} → ${n} (demo)`,...a.activity]}),'Đã cập nhật số lượng nguồn');
    } else patch(selected.id,a=>({...a,proposed:n,manualPrice:true,activity:[`Đơn giá đề xuất do người dùng chỉnh: ${vnd(n)}`, ...a.activity]}),'Đã cập nhật giá do người dùng quyết định');
  };

  const updateSpecs=()=>{
    const next=identityDraft?.trim();
    if(!next) return;
    patch(selected.id,a=>({...a,specs:next,needsRecheck:classifyIdentityChange(a.originalSpecs,next),resolution:'',activity:[`Đã sửa đặc điểm thành: ${next}`, ...a.activity]}),'Đã sửa đặc điểm; cần phân loại nếu có thay đổi nhận dạng');
    setIdentityClass('');
  };
  const resolveIdentity=()=>{
    if(!identityClass)return;
    patch(selected.id,a=>({...a,resolution:identityClass,needsRecheck:classifyIdentityChange(a.originalSpecs,a.specs),activity:[
      identityClass==='correct'?'Đã tạo ĐỀ XUẤT cập nhật tri thức (mô phỏng, chưa duyệt)':identityClass==='new'?'Đã tạo ĐỀ XUẤT biến thể mới (mô phỏng)':'Chỉ sửa riêng trong hồ sơ',
      ...a.activity,
    ]}),'Đã ghi nhận phân loại trong prototype; không cập nhật Kho tri thức thật');
  };
  const addSimilar=(s:Similar)=>{
    patch(selected.id,a=>({...a,survey:s.survey,transportPercent:a.transportPercent??5,
      proposed:a.manualPrice?a.proposed:(a.proposed??suggestedPrice(s.survey,a.transportPercent??5)),
      sources:[...a.sources,{...s.source,id:s.source.id+'-'+a.id,isPrimary:a.sources.length===0}],
      origin:'manual',match:'manual',activity:[`Đã chọn nguồn tham khảo ${s.id}; chưa phải chấp nhận làm cơ sở`,...a.activity]}),
      'Đã chọn nguồn tham khảo và liên kết chứng cứ (mô phỏng)');
  };
  const changeTextEvidence=(text:string)=>{
    patch(selected.id,a=>{
      const source=a.sources[0]??exampleSource('NG-MANUAL-'+a.id,'Nguồn nhập thủ công',a.survey);
      const urls=extractLinks(text);
      const next={...source,links:[...new Set([...source.links,...urls])],explanation:text};
      return {...a,sources:[next,...a.sources.slice(1)],origin:a.origin==='none'?'manual':a.origin};
    },'Đã cập nhật diễn giải/link trong phiên mô phỏng');
  };
  const pasteEvidence=(event:ClipboardEvent<HTMLTextAreaElement>)=>{
    const files=[...event.clipboardData.items].filter(i=>i.kind==='file'&&i.type.startsWith('image/'));
    if(!files.length) return;
    event.preventDefault();
    for(const item of files){
      const f=item.getAsFile(); if(!f) continue;
      if(f.size>2*1024*1024){setNotice('Ảnh vượt 2 MB — prototype không nhận ảnh này.');continue;}
      const reader=new FileReader();
      reader.onload=()=>{
        const data=String(reader.result??''); if(!data.startsWith('data:image/'))return;
        patch(selected.id,a=>{
          const source=a.sources[0]??exampleSource('NG-MANUAL-'+a.id,'Nguồn nhập thủ công',a.survey);
          const image:EvidenceImage={id:`${a.id}-${Date.now()}-${Math.random()}`,name:f.name||'Ảnh từ clipboard',dataUrl:data};
          return {...a,sources:[{...source,images:[...source.images,image]},...a.sources.slice(1)],origin:a.origin==='none'?'manual':a.origin};
        },'Ảnh clipboard được hiển thị tạm trong bộ nhớ prototype');
      };
      reader.readAsDataURL(f);
    }
  };
  const setOrCreateSource=(field:'survey'|'transport'|'proposed', raw:string)=>{
    const number=raw.trim()===''?null:Number(raw);
    if(number!==null&&(!Number.isFinite(number)||number<0))return;
    patch(selected.id,a=>{
      if(field==='proposed')return {...a,proposed:number,manualPrice:true};
      const survey=field==='survey'?number:a.survey;
      const transport=field==='transport'?number:a.transportPercent;
      return {...a,survey,transportPercent:transport,
        proposed:a.manualPrice?a.proposed:suggestedPrice(survey,transport,transport!==null)};
    },field==='proposed'?'Đã sửa giá đề xuất':'Đã cập nhật dữ liệu khảo sát/gợi ý');
  };
  const syncScroll=(from:'top'|'table')=>{
    if(syncing.current)return; syncing.current=true;
    const source=from==='top'?topScrollbar.current:tableScrollbar.current;
    const target=from==='top'?tableScrollbar.current:topScrollbar.current;
    if(source&&target)target.scrollLeft=source.scrollLeft;
    requestAnimationFrame(()=>{syncing.current=false;});
  };
  const moveFocusNext=(e:KeyboardEvent<HTMLButtonElement>,id:string)=>{
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){
      e.preventDefault();const index=visible.findIndex(a=>a.id===id);
      const next=visible[index+(e.key==='ArrowDown'?1:-1)]; if(next)gotoAsset(next.id);
    }
  };
  const finalizeVersion=()=>{
    if(!ack)return;
    setAssets(prev=>nextViewed(prev,selectedId));setExportedVersion(n=>n+1);
    setExportSignature(currentSignature);setAck(false);
    setNotice('Đã xác nhận phiên bản demo (chỉ bộ nhớ trình duyệt). CHƯA tạo file Excel hoặc lưu máy chủ.');
  };

  return <div className="app-layout">
    <SideNav collapsed={navCollapsed} onToggle={()=>setNavCollapsed(v=>!v)} onShowSummary={()=>switchRoute('summary')} onShowWorkbench={()=>switchRoute('workbench')} route={route}/>
    <div className="app-main">
      <header className="topbar">
        <Breadcrumb aria-label="Vị trí hiện tại">
          <BreadcrumbItem><BreadcrumbButton onClick={()=>switchRoute('workbench')}>Yêu cầu sơ bộ</BreadcrumbButton></BreadcrumbItem>
          <BreadcrumbDivider/>
          <BreadcrumbItem><BreadcrumbButton onClick={()=>switchRoute('workbench')}>SB-001</BreadcrumbButton></BreadcrumbItem>
          <BreadcrumbDivider/>
          <BreadcrumbItem><BreadcrumbButton aria-current="page">{route==='summary'?'Tổng kết kết quả':'Phân tích danh mục'}</BreadcrumbButton></BreadcrumbItem>
        </Breadcrumb>
        <div className="topbar-right"><span className="demo-indicator">DEMO — KHÔNG CÓ DỮ LIỆU THẬT</span><span className="user-dot">PM</span></div>
      </header>
      <div className="page">
        <div className="page-header">
          <div><div className="eyebrow">YÊU CẦU SƠ BỘ / SB-001</div><h1 ref={titleRef} tabIndex={-1}>{route==='workbench'?'Phân tích danh mục':'Tổng kết kết quả sơ bộ'}</h1>
            <p className="muted">{route==='workbench'?'Đối chiếu Kho tri thức đã hoàn tất · Nhân viên rà soát từ trên xuống':'Kiểm tra cảnh báo, xác nhận tổng thể và quản lý phiên bản Excel'}</p></div>
          <div className="header-actions">
            {route==='summary'?<Button icon={<ArrowLeft20Regular/>} onClick={()=>switchRoute('workbench')}>Quay lại danh mục</Button>:<>
              <Button appearance="secondary" icon={<PanelRight20Regular/>} onClick={()=>setDrawerOpen(v=>!v)}>{isDrawerOpen?'Đóng panel':'Mở panel'}</Button>
              <Button appearance="primary" icon={<ArrowRight20Regular/>} onClick={()=>switchRoute('summary')}>Tổng kết & xuất</Button>
            </>}
          </div>
        </div>
        <div className="prototype-note"><Info20Regular/><span>Bản mẫu UX v02 dùng Fluent UI React v9. Thao tác chỉ cập nhật bộ nhớ trang, không ghi vào VALORA.</span></div>
        {notice&&<MessageBar intent="info" className="notice"><MessageBarBody>{notice}</MessageBarBody><Button size="small" appearance="subtle" icon={<Dismiss20Regular/>} aria-label="Đóng thông báo" onClick={clearNotice}/></MessageBar>}
        {route==='workbench'?<>
          <div className="stats-strip">
            <div><span>Tổng tài sản</span><strong>{assets.length}</strong></div>
            <div><span>VALORA đã tự điền</span><strong>{assets.filter(a=>a.origin==='auto').length}</strong></div>
            <div><span>Đã xem</span><strong>{assets.filter(a=>a.viewed).length}/{assets.length}</strong></div>
            <div><span>Thiếu đơn giá</span><strong>{summary.missingPrice}</strong></div>
            <div className="stats-last"><span>Excel gần nhất</span><strong>{exportedVersion?`v${String(exportedVersion).padStart(2,'0')}`:'Chưa xuất'}</strong>{changedSinceExport&&<Badge appearance="tint" color="warning" size="small">Có thay đổi chưa xuất</Badge>}</div>
          </div>
          <div className="workarea">
            <section className="grid-area" aria-label="Bảng danh mục tài sản">
              <div className="grid-toolbar"><Field aria-label="Tìm tài sản"><Input contentBefore={<Search20Regular/>} placeholder="Tìm tài sản, model, công suất..." value={search} onChange={(_,d)=>setSearch(d.value)}/></Field>
                <Select aria-label="Lọc tài sản" value={filter} onChange={(_,d)=>setFilter(d.value)}><option value="all">Tất cả</option><option value="unviewed">Chưa xem</option><option value="missing">Thiếu giá</option><option value="recheck">Cần kiểm tra lại</option></Select>
                <span className="muted tiny">{visible.length} / {assets.length} dòng</span>
              </div>
              <div className="top-scroll" ref={topScrollbar} onScroll={()=>syncScroll('top')} aria-label="Thanh cuộn ngang phía trên bảng" tabIndex={0}><div className="top-scroll-inner"/></div>
              <div className="table-scroll" ref={tableScrollbar} onScroll={()=>syncScroll('table')}>
                <Table aria-label="Danh mục tài sản sơ bộ" size="small" className="asset-table">
                  <TableHeader><TableRow>
                    <TableHeaderCell className="pin-stt">STT</TableHeaderCell>
                    <TableHeaderCell className="pin-name">Tài sản</TableHeaderCell>
                    <TableHeaderCell>Đặc điểm</TableHeaderCell>
                    <TableHeaderCell>ĐVT</TableHeaderCell>
                    <TableHeaderCell>SL nguồn</TableHeaderCell>
                    <TableHeaderCell>Đơn giá KH</TableHeaderCell>
                    <TableHeaderCell>Thành tiền KH</TableHeaderCell>
                    <TableHeaderCell>Giá khảo sát</TableHeaderCell>
                    <TableHeaderCell>Đơn giá đề xuất</TableHeaderCell>
                    <TableHeaderCell>Thành tiền đề xuất</TableHeaderCell>
                    <TableHeaderCell>Nguồn</TableHeaderCell>
                    <TableHeaderCell>Chứng cứ</TableHeaderCell>
                    <TableHeaderCell>Trạng thái</TableHeaderCell>
                  </TableRow></TableHeader>
                  <TableBody>{visible.map(a=>{
                    const idx=assets.findIndex(x=>x.id===a.id);
                    const count=a.sources.reduce((n,s)=>n+s.links.length+s.images.length,0);
                    return <TableRow className={`${a.id===selected.id?'selected-row':''}`} key={a.id}>
                      <TableCell className="pin-stt">{idx+1}</TableCell>
                      <TableCell className="pin-name"><Button appearance="transparent" size="small" className="asset-link" onKeyDown={e=>moveFocusNext(e,a.id)} onClick={()=>gotoAsset(a.id)}><span>{a.name}</span><small>{a.id}</small></Button></TableCell>
                      <TableCell className="spec-cell">{a.specs}</TableCell>
                      <TableCell>{a.unit}</TableCell><TableCell className="num">{a.qty}{a.qty!==a.originalQty&&<span title={`Excel gốc: ${a.originalQty}`} className="qty-mark">*</span>}</TableCell>
                      <TableCell className="num">{vnd(a.customerPrice)}</TableCell><TableCell className="num">{vnd(amount(a.customerPrice,a.qty))}</TableCell>
                      <TableCell className="num">{vnd(a.survey)}</TableCell><TableCell className="num price">{vnd(a.proposed)}</TableCell>
                      <TableCell className="num">{vnd(amount(a.proposed,a.qty))}</TableCell>
                      <TableCell className="num">{a.sources.length}</TableCell><TableCell className="num">{count}</TableCell>
                      <TableCell><Status asset={a}/>{a.viewed&&<span className="viewed">Đã xem</span>}</TableCell>
                    </TableRow>;
                  })}</TableBody>
                </Table>
              </div>
              <div className="grid-bottom"><span className="muted tiny">* SL nguồn khác giá trị Excel gốc · Cuộn ngang bảng bằng thanh trên hoặc dưới</span><span className="tiny muted">Giữ STT và tên tài sản khi cuộn</span></div>
            </section>
            {isDrawerOpen&&<InlineDrawer open={isDrawerOpen} position="end" size="large" className="asset-drawer">
              <DrawerHeader><DrawerHeaderTitle action={<Button appearance="subtle" size="small" icon={<Dismiss20Regular/>} onClick={()=>setDrawerOpen(false)} aria-label="Đóng chi tiết tài sản"/>}>
                <span className="drawer-eyebrow">Tài sản {selectedIndex+1}/{assets.length} · {selected.id}</span><span className="drawer-name">{selected.name}</span>
              </DrawerHeaderTitle></DrawerHeader>
              <DrawerBody className="drawer-scroll">
                <div className="panel-chips"><Status asset={selected}/>{selected.viewed&&<Badge appearance="outline" color="informative" size="small">Đã xem</Badge>}{selected.match==='high'&&<Badge appearance="outline" size="small">Khớp đủ tin cậy</Badge>}</div>
                <TabList selectedValue={detailTab} onTabSelect={(_,d)=>setDetailTab(d.value as DetailTab)} size="small" aria-label="Nội dung tài sản" className="detail-tabs"><Tab value="price">Giá & chứng cứ</Tab><Tab value="specs">Đặc điểm & SL</Tab><Tab value="history">Lịch sử</Tab></TabList>
                {detailTab==='price'&&<section className="panel-stack" aria-label="Giá và chứng cứ">
                  {selected.needsRecheck&&<MessageBar intent="warning"><MessageBarBody><MessageBarTitle>Cần kiểm tra lại nguồn</MessageBarTitle>Thông số/điều kiện nguồn chưa được xác nhận phù hợp. Không tự thay giá nhân viên.</MessageBarBody></MessageBar>}
                  {selected.id==='TS-001'&&<MessageBar intent="warning"><MessageBarBody><MessageBarTitle>Chênh lệch giữa các nguồn</MessageBarTitle>100 triệu và 145 triệu. Nhân viên xem xét trong bước rà soát này, không thêm bước phê duyệt giá.</MessageBarBody></MessageBar>}
                  {selected.sources.length===0?<div className="empty"><Database20Regular/><strong>Chưa có nguồn đủ tin cậy</strong><span>Tìm tài sản tương tự hoặc nhập thông tin khảo sát mới.</span></div>:<>
                    <div className="section-title">Nguồn giá và chứng cứ</div>
                    {selected.sources.map(s=><SourceCard source={s} key={s.id} onPrefer={()=>patch(selected.id,a=>({
                      ...a,survey:s.price,proposed:a.manualPrice?a.proposed:suggestedPrice(s.price,a.transportPercent,a.transportPercent!==null),
                      sources:a.sources.map(src=>({...src,isPrimary:src.id===s.id})),
                      activity:[`Nhân viên chọn nguồn ưu tiên: ${s.name}`,...a.activity],
                    }),'Đã đổi nguồn tham khảo ưu tiên; giữ giá thủ công nếu đã chỉnh')}/>)}
                  </>}
                  {selected.match!=='high'&&<section className="similar-panel">
                    <div className="section-title">Tìm tài sản tương tự</div>
                    <Input contentBefore={<Search20Regular/>} aria-label="Tìm tài sản tương tự" placeholder="Model, hãng, công suất..." value={similarSearch} onChange={(_,d)=>setSimilarSearch(d.value)}/>
                    {similar.filter(s=>!similarSearch||s.name.toLocaleLowerCase('vi').includes(similarSearch.toLocaleLowerCase('vi'))).map(s=><div className="similar-result" key={s.id}>
                      <strong>{s.name}</strong><span className="tiny">Giống: {s.similarity}</span><span className="muted tiny">Khác: {s.differences}</span>
                      <div className="similar-actions"><span>{vnd(s.survey)} đ</span><Button size="small" appearance="secondary" onClick={()=>addSimilar(s)}>Dùng làm tham khảo</Button></div>
                    </div>)}
                  </section>}
                  {selected.sources.length>0&&<div className="two-fields">
                    <Field label="Điều kiện VAT nguồn ưu tiên"><Select aria-label="Điều kiện VAT" value={selected.sources.find(x=>x.isPrimary)?.vat??'Chưa rõ VAT'} onChange={(_,d)=>patch(selected.id,a=>({...a,sources:a.sources.map(x=>x.isPrimary?{...x,vat:d.value}:x)}),'Đã sửa điều kiện VAT của nguồn')}>
                      <option value="Chưa bao gồm VAT">Chưa bao gồm</option><option value="Đã bao gồm VAT">Đã bao gồm</option><option value="Chưa rõ VAT">Chưa xác định</option>
                    </Select></Field>
                    <Field label="Điều kiện vận chuyển nguồn"><Select aria-label="Điều kiện vận chuyển" value={selected.sources.find(x=>x.isPrimary)?.transport??'Chưa rõ vận chuyển'} onChange={(_,d)=>patch(selected.id,a=>({...a,sources:a.sources.map(x=>x.isPrimary?{...x,transport:d.value}:x)}),'Đã sửa điều kiện vận chuyển của nguồn')}>
                      <option value="Chưa bao gồm vận chuyển">Chưa bao gồm</option><option value="Đã bao gồm vận chuyển">Đã bao gồm</option><option value="Chưa rõ vận chuyển">Chưa xác định</option>
                    </Select></Field>
                  </div>}
                  <Divider/>
                  <div className="section-title">Giá làm việc (VNĐ)</div>
                  <div className="two-fields">
                    <Field label="Đơn giá khảo sát"><Input type="number" min={0} value={draftSurvey??String(selected.survey??'')} onChange={(_,d)=>{setDraftSurvey(d.value);}} onBlur={()=>{if(draftSurvey!==null){setOrCreateSource('survey',draftSurvey);setDraftSurvey(null);}}}/></Field>
                    <Field label="Vận chuyển (%)" hint="Để trống nếu chưa rõ"><Input type="number" min={0} value={draftTransport??String(selected.transportPercent??'')} onChange={(_,d)=>setDraftTransport(d.value)} onBlur={()=>{if(draftTransport!==null){setOrCreateSource('transport',draftTransport);setDraftTransport(null);}}}/></Field>
                  </div>
                  <div className="suggestion">Giá đề xuất gợi ý: <strong>{vnd(suggestedPrice(selected.survey,selected.transportPercent,selected.transportPercent!==null))} đ</strong></div>
                  <Field label="Đơn giá đề xuất — người dùng quyết định" hint={selected.manualPrice?'Giá đã được người dùng chỉnh; không tự ghi đè':'Có thể sửa độc lập với công thức gợi ý'}>
                    <Input type="number" min={0} value={draftProposed??String(selected.proposed??'')} onChange={(_,d)=>setDraftProposed(d.value)} onBlur={()=>{if(draftProposed!==null){setOrCreateSource('proposed',draftProposed);setDraftProposed(null);}}}/>
                  </Field>
                  <div className="section-title">Diễn giải, liên kết và ảnh</div>
                  <Textarea resize="vertical" aria-label="Diễn giải và dán chứng cứ" placeholder="Nhập diễn giải, dán URL hoặc Ctrl+V ảnh trực tiếp. Không cần đăng ký chứng cứ lại." value={draftNote??selected.note} onChange={(_,d)=>{setDraftNote(d.value);}} onPaste={pasteEvidence} onBlur={()=>{if(draftNote!==null&&draftNote!==selected.note){patch(selected.id,a=>({...a,note:draftNote}),'Đã cập nhật diễn giải');changeTextEvidence(draftNote);setDraftNote(null);}}}/>
                  <div className="tiny muted">Ảnh dán được xem trước trong thẻ nguồn và cột chứng cứ; chỉ lưu tạm trong trang, tối đa 2 MB/ảnh. URL minh họa không phải nguồn xác minh thực tế.</div>
                </section>}
                {detailTab==='specs'&&<section className="panel-stack" aria-label="Thông tin tài sản và nhận dạng">
                  <div className="section-title">Thông tin tài sản</div>
                  <Field label="Tên gốc từ Excel"><Input value={selected.name} readOnly/></Field>
                  <Field label="Đặc điểm hiện tại"><Textarea resize="vertical" value={identityDraft??selected.specs} onChange={(_,d)=>setIdentityDraft(d.value)}/></Field>
                  <Button size="small" appearance="secondary" onClick={()=>{if(identityDraft!==null){updateSpecs();setIdentityDraft(null);}}}>Lưu thay đổi đặc điểm (demo)</Button>
                  <div className="two-fields"><Field label="ĐVT"><Input readOnly value={selected.unit}/></Field><Field label="SL nguồn" hint={`SL Excel gốc: ${selected.originalQty}`}><Input type="number" min={0} value={String(selected.qty)} onChange={(_,d)=>changeField('qty',d.value)}/></Field></div>
                  {classifyIdentityChange(selected.originalSpecs,selected.specs)&&!selected.resolution&&<div className="identity-prompt">
                    <strong>Đặc điểm nhận dạng đã thay đổi</strong><p className="muted tiny">Chọn cách hiểu thay đổi này. Không tự sửa Kho tri thức dùng chung.</p>
                    <RadioGroup value={identityClass} onChange={(_,d)=>setIdentityClass(d.value as KnowledgeDecision)}>
                      <Radio value="correct" label="Đề xuất sửa bản ghi tri thức hiện có"/>
                      <Radio value="new" label="Tài sản hoặc biến thể mới"/>
                      <Radio value="case" label="Chỉ sửa hồ sơ này"/>
                    </RadioGroup>
                    <Button size="small" appearance="primary" disabled={!identityClass} onClick={resolveIdentity}>Ghi nhận phân loại</Button>
                  </div>}
                  {selected.resolution&&<MessageBar intent="info"><MessageBarBody>{selected.resolution==='correct'?'Đề xuất sửa tri thức đã tạo trong bản mẫu; chưa duyệt.':selected.resolution==='new'?'Ứng viên biến thể mới trong bản mẫu; chưa tạo bản ghi thật.':'Chỉ chỉnh sửa hồ sơ, không cập nhật Kho tri thức.'}</MessageBarBody></MessageBar>}
                  {selected.needsRecheck&&<span className="tiny muted">Nguồn trước đây cần rà soát lại theo thuộc tính mới; giá đề xuất đã nhập được giữ.</span>}
                </section>}
                {detailTab==='history'&&<section className="panel-stack" aria-label="Lịch sử và nguồn gốc">
                  <div className="section-title">Xem nguồn gốc · Xem lịch sử</div>
                  <div className="history-list">{selected.activity.map((ev,i)=><div key={i}><span className="history-dot"/><span>{ev}</span></div>)}</div>
                  <p className="tiny muted">Lịch sử trong bản mẫu là dữ liệu minh họa. Hệ thống thật cần bản ghi actor, thời điểm, trước/sau và phiên bản tri thức.</p>
                </section>}
              </DrawerBody>
              <DrawerFooter className="drawer-footer"><span className="tiny muted">Không yêu cầu chấp nhận từng dòng</span><div className="footer-buttons">
                <Button size="small" icon={<ChevronLeft20Regular/>} disabled={selectedIndex===0} onClick={()=>gotoByOffset(-1)}>Trước</Button>
                <Button size="small" appearance="primary" icon={<ChevronRight20Regular/>} iconPosition="after" disabled={selectedIndex===assets.length-1} onClick={()=>gotoByOffset(1)}>Tiếp theo</Button>
              </div></DrawerFooter>
            </InlineDrawer>}
          </div>
          <div className="demo-scenarios"><span className="tiny muted">TÌNH HUỐNG THỬ NHANH (CHỈ CÓ TRONG PROTOTYPE)</span><Button size="small" appearance="subtle" onClick={()=>gotoAsset('TS-001')}>01 · Đã tự điền</Button><Button size="small" appearance="subtle" onClick={()=>gotoAsset('TS-002')}>02 · Thiếu nguồn</Button><Button size="small" appearance="subtle" onClick={()=>{gotoAsset('TS-003');setDetailTab('specs');}}>03 · Sửa đặc điểm</Button></div>
        </>:<section className="summary-screen" aria-label="Tổng kết kết quả sơ bộ">
          <div className="summary-head"><h2>Kiểm tra trước khi xuất</h2><p className="muted">Các nhóm cảnh báo có thể chồng lấp. Không tự coi tài sản chưa xem là đã được rà soát.</p></div>
          <div className="summary-cards">
            <div><span>Đã xem</span><strong>{assets.length-summary.unviewed}/{assets.length}</strong></div>
            <div><span>Chưa xem</span><strong>{summary.unviewed}</strong></div>
            <div><span>Thiếu đơn giá</span><strong>{summary.missingPrice}</strong></div>
            <div><span>Thiếu chứng cứ</span><strong>{summary.missingEvidence}</strong></div>
            <div><span>Cần kiểm tra lại</span><strong>{summary.recheck}</strong></div>
          </div>
          <div className="summary-columns"><section className="summary-panel"><h3>Các tài sản cần chú ý</h3>
            {assets.filter(a=>!a.viewed||a.proposed===null||a.needsRecheck).map(a=><div className="summary-row" key={a.id}><div><strong>{a.name}</strong><small>{a.id} · {[!a.viewed?'Chưa xem':'',a.proposed===null?'Thiếu giá':'',a.needsRecheck?'Cần kiểm tra nguồn':''].filter(Boolean).join(' · ')}</small></div><Button size="small" appearance="secondary" onClick={()=>rowDisplayLink(a.id)}>Xử lý</Button></div>)}
            <MessageBar intent="warning"><MessageBarBody>Đơn giá chưa xác định được để trống và không tính vào tổng giá trị đã xác định. Cảnh báo trong OS-G1 không đồng nghĩa quyết định thẩm định cuối.</MessageBarBody></MessageBar>
          </section><section className="summary-panel"><h3>Xem trước kết quả</h3>
            <div className="total-price"><span>Tổng thành tiền đề xuất đã xác định</span><strong>{vnd(total)} đ</strong><small>Chỉ cộng dòng có giá và số lượng xác định; không có dòng chứng cứ phụ.</small></div>
            <div className="summary-meta"><span>Phiên bản đã xác nhận (mô phỏng)</span><strong>{exportedVersion?`v${String(exportedVersion).padStart(2,'0')}`:'Chưa có'}</strong></div>
            {changedSinceExport&&<Badge appearance="tint" color="warning">Có thay đổi chưa xuất thành phiên bản mới</Badge>}
            <Divider/>
            <Checkbox checked={ack} onChange={(_,d)=>setAck(d.checked===true)} label="Tôi đã xem cảnh báo và xác nhận sử dụng dữ liệu hiện tại cho kết quả sơ bộ (mô phỏng)."/>
            <Button appearance="primary" disabled={!ack} onClick={finalizeVersion}>Xác nhận phiên bản minh họa</Button>
            <span className="tiny muted">Không tạo tệp Excel thật. Bản triển khai sau này phải xuất một bảng Excel có URL và ảnh chứng cứ nhúng, lưu snapshot độc lập.</span>
            <Divider/>
            <h3>Lịch sử phiên bản (bộ nhớ trang)</h3>
            {exportedVersion===0?<p className="muted">Chưa có phiên bản được tạo trong mô phỏng.</p>:Array.from({length:exportedVersion},(_,i)=><div className="summary-row" key={i}><strong>Phiên bản v{String(exportedVersion-i).padStart(2,'0')}</strong><Badge appearance="outline" color="informative">Bản chụp minh họa</Badge></div>)}
          </section></div>
        </section>}
        <footer className="page-footer"><span>VALORA UX-G1.15 v02 · Fluent UI React v9 · Dữ liệu hoàn toàn giả lập</span><span>Prototype duyệt giao diện, không phải UAT #203</span></footer>
      </div>
    </div>
  </div>;
}
