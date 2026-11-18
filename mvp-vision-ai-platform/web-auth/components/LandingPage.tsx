import React from 'react';
import { useDashboardLink, withDashboardLink } from './useDashboardLink';

type Lang = 'ko' | 'en';

// public/ assets are served relative to the app root, not next.config.js's basePath,
// so absolute src paths need the basePath prepended manually to resolve under /auth in production.
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || '';

function withBasePath(path: string) {
  return `${BASE_PATH}${path}`;
}

export interface LandingPageProps {
  lang?: Lang;
  isAuthenticated?: boolean;
  userName?: string | null;
  onLogin?: () => void;
  onLogout?: () => void;
}

interface NavLink {
  label: string;
  href: string;
}

interface ProofPoint {
  value: string;
  label: string;
}

interface Strength {
  title: string;
  description: string;
}

interface ModuleFlowStep {
  title: string;
  description: string;
  image?: string;
}

interface ModuleFeature {
  title: string;
  bullets: string[];
}

interface ProductModule {
  badge: string;
  taglines: string[];
  sectionTitle: string;
  sectionSubtitle: string;
  flow: ModuleFlowStep[];
  features: ModuleFeature[];
}

interface UseCase {
  title: string;
  category: string;
  defectNote: string;
  trainerModels: string;
  runnerHighlight: string;
  runnerNotes: string[];
  imagePath?: string;
}

interface FlowItem {
  title: string;
  description: string;
}

interface FlowOutcome {
  value: string;
  label: string;
  caption: string;
}

interface SignalContent {
  eyebrow: string;
  title: string;
  lead: string;
  beforeTitle: string;
  afterTitle: string;
  beforeFlow: string[];
  afterFlow: string[];
  before: FlowItem[];
  after: FlowItem[];
  outcomes: FlowOutcome[];
}

interface Content {
  nav: {
    links: NavLink[];
    start: string;
  };
  hero: {
    eyebrow: string;
    titleTop: string;
    titleMain: string;
    lead: string;
    primary: string;
    secondary: string;
  };
  proof: ProofPoint[];
  labelerTrainer: ProductModule;
  runner: ProductModule;
  cases: {
    eyebrow: string;
    title: string;
    lead: string;
    items: UseCase[];
  };
  environment: {
    eyebrow: string;
    title: string;
    lead: string;
    points: Strength[];
  };
  cta: {
    title: string;
    lead: string;
    primary: string;
    secondary: string;
  };
  footer: string;
  ui: {
    dataset: string;
    training: string;
    runner: string;
    mediaPhoto: string;
    mediaVideo: string;
    assetReady: string;
    metric: string;
    model: string;
    status: string;
    complete: string;
    live: string;
    previous: string;
    next: string;
  };
}

const SIGNAL_CONTENT: Record<Lang, SignalContent> = {
  ko: {
    eyebrow: 'BEFORE / AFTER',
    title: '흩어진 검사 AI 이력을 하나로',
    lead: '기존에는 검사기 이미지 추출부터 offline 학습과 모델 export까지 단계가 끊겨 이력 추적과 성능 재현이 어려웠습니다. DICE는 이 과정을 하나의 제품 흐름으로 연결합니다.',
    beforeTitle: '기존 AI 검사 흐름',
    afterTitle: 'DICE 통합 흐름',
    beforeFlow: ['검사기 이미지 추출', '이미지 선별', 'offline 레이블링', 'offline 학습', '모델 export'],
    afterFlow: ['Labeler', 'Trainer', 'Runner'],
    before: [
      { title: '파일 단위 전달', description: '이미지 선별, 레이블링, 학습이 offline 파일 전달로 이어집니다.' },
      { title: '이력 추적 어려움', description: '어떤 이미지와 라벨, 파라미터가 모델로 이어졌는지 남기기 어렵습니다.' },
      { title: '성능 재현 어려움', description: 'export된 모델의 학습 조건과 결과를 다시 재현하기 어렵습니다.' },
    ],
    after: [
      { title: '데이터셋 이력 연결', description: 'Labeler에서 이미지, 라벨, 검수 상태를 데이터셋 버전으로 관리합니다.' },
      { title: '학습 결과 추적', description: 'Trainer에서 학습 Job, metric, artifact를 같은 프로젝트 흐름에 남깁니다.' },
      { title: '실행 준비까지 연결', description: '모델 export와 Runner 실행 준비가 제품 흐름 안에서 이어집니다.' },
    ],
    outcomes: [
      { value: '1 flow', label: '통합 흐름', caption: 'Labeler → Trainer → Runner' },
      { value: 'Traceable', label: '이력 추적', caption: 'dataset, metric, export 이력' },
      { value: 'Reproducible', label: '성능 재현', caption: '학습 조건과 결과 연결' },
    ],
  },
  en: {
    eyebrow: 'BEFORE / AFTER',
    title: 'Make inspection AI traceable',
    lead: 'Traditional workflows move from image extraction to offline labeling, offline training, and model export with broken history. DICE connects the whole process in one product flow.',
    beforeTitle: 'Traditional AI inspection flow',
    afterTitle: 'DICE connected flow',
    beforeFlow: ['Extract images', 'Select images', 'Label offline', 'Train offline', 'Export model'],
    afterFlow: ['Labeler', 'Trainer', 'Runner'],
    before: [
      { title: 'File-based handoff', description: 'Image selection, labeling, and training move through offline files.' },
      { title: 'Hard to trace', description: 'It is difficult to keep images, labels, parameters, and model output connected.' },
      { title: 'Hard to reproduce', description: 'Exported models are hard to reproduce from the original training conditions.' },
    ],
    after: [
      { title: 'Connected dataset history', description: 'Labeler keeps images, labels, review status, and dataset versions together.' },
      { title: 'Tracked training results', description: 'Trainer keeps jobs, metrics, and artifacts in the same project flow.' },
      { title: 'Connected runtime prep', description: 'Model export and Runner preparation continue inside the product flow.' },
    ],
    outcomes: [
      { value: '1 flow', label: 'Integrated flow', caption: 'Labeler → Trainer → Runner' },
      { value: 'Traceable', label: 'History tracking', caption: 'Dataset, metrics, export history' },
      { value: 'Reproducible', label: 'Performance replay', caption: 'Training conditions and results' },
    ],
  },
};

const CONTENT: Record<Lang, Content> = {
  ko: {
    nav: {
      links: [
        { label: 'Defect', href: '/defect' },
        { label: 'Labeler', href: '/labeler' },
        { label: 'Trainer', href: '/platform' },
        { label: 'Runner', href: '/runner' },
        { label: 'Docs', href: '/docs/ko/guide/overview' },
        { label: 'Download', href: '/downloads' },
        { label: 'Activation', href: '/activation' },
      ],
      start: '시작하기',
    },
    hero: {
      eyebrow: 'DICE Vision AI Suite',
      titleTop: 'Platform for',
      titleMain: 'Manufacturing AI Inspection',
      lead: '제조 검사 AI를 위한 데이터셋, 학습, 실행 플랫폼',
      primary: '시작하기',
      secondary: '문서 보기',
    },
    proof: [
      { value: 'Label', label: '라벨링과 검수' },
      { value: 'Train', label: '학습과 성능 추적' },
      { value: 'Export', label: '모델 변환과 관리' },
      { value: 'Run', label: '현장 추론 실행' },
    ],
    labelerTrainer: {
      badge: 'DICE-Labeler/Trainer',
      taglines: ['AI 학습 데이터 라벨링 솔루션: Labeler', 'AI 학습 플랫폼 솔루션: Trainer'],
      sectionTitle: '검사 AI 모델 개발을 한번에 관리하다',
      sectionSubtitle: '데이터 관리부터 학습, 배포, 추론까지 End-to-End AI Vision Workflow',
      flow: [
        { title: 'Labeling', description: '직관적인 Labeling Tool을 이용한 학습 데이터 생성' },
        { title: 'Train', description: '검사 목적/상황에 맞는 다양한 모델 지원' },
        { title: 'Analysis', description: '학습된 모델의 성능 검증' },
        { title: 'Export', description: '모델 Export 및 Export History 관리' },
      ],
      features: [
        {
          title: '쉬운 학습 / Labeling',
          bullets: ['AI 전문가가 아니더라도 가능한 직관적인 학습 / Labeling', '몇 번의 클릭으로 완성하는 Vision 검사 모델'],
        },
        {
          title: '높은 정확도 / 성능',
          bullets: ['정확한 불량 검출을 위해 최적화 된 AI Model Training', '데이터 기반 학습으로 검사 품질 지속 개선'],
        },
        {
          title: '빠른 모델 생성 / 적용',
          bullets: ['빠른 학습 Cycle로 현장 대응력을 극대화', '개발 기간을 줄이고, 생산 적용 속도는 높임'],
        },
        {
          title: '강건한 모델 학습',
          bullets: ['데이터 불균형 등 현실적인 데이터 제약 대응', '제한적인 데이터 환경에서 안정적인 Model 학습 지원'],
        },
      ],
    },
    runner: {
      badge: 'DICE-Runner',
      taglines: ['AI 검사 고성능 추론 솔루션: Runner'],
      sectionTitle: '검사 AI 모델을 검사에 적용하다',
      sectionSubtitle: '모델 배포부터 추론, 운영 관리까지 End-to-End AI Vision Workflow',
      flow: [
        { title: 'Model', description: '등록된 모델 및 버전 관리', image: '/assets/screens/runner_model.png' },
        { title: 'Deploy', description: '검사 추론 환경에 맞는 AI 모델 배포 지원', image: '/assets/screens/runner_deploy.jpg' },
        { title: 'Inference', description: '대량 요청에도 안정적인 추론 및 추론 시뮬레이션 제공', image: '/assets/screens/runner_inference.png' },
        { title: 'Monitoring', description: '운영 환경에서의 안정적인 PC 상태 / 모델 모니터링', image: '/assets/screens/runner_monitoring.png' },
      ],
      features: [
        {
          title: '고속 추론 / 높은 처리 성능',
          bullets: ['Multi Worker 기반 병렬 추론으로 실시간 검사 지원', 'GPU/CPU 최적화를 통한 빠른 응답 및 높은 처리량'],
        },
        {
          title: '쉬운 모델 적용',
          bullets: ['검사 환경에 맞게 다양한 모델 타입으로 간편 배포 지원', '빠른 모델 교체 및 모델 확장 가능'],
        },
        {
          title: '쉬운 시스템 연동',
          bullets: ['REST API 기반으로 검사 시스템과 간편한 연동 지원', '다양한 제조 환경에 빠르고 유연한 AI 적용 지원'],
        },
        {
          title: '안정적인 AI Service Operation',
          bullets: ['추론 성능 및 Service 상태 모니터링', '지속적인 AI 검사 품질 및 운영 안정성 확보'],
        },
      ],
    },
    cases: {
      eyebrow: 'USE CASES',
      title: '적용 사례',
      lead: 'AI 기반 비전 검사 적용 실제 사례입니다.',
      items: [
        {
          title: 'MX 메탈 최종 외관 검사',
          category: 'Surface Inspection',
          defectNote: '스크래치, 찍힘, 얼룩, 백점, 분절부 얼룩 등 다유형의 불량 검출 필요',
          trainerModels: '5종 AI 모델 (Detection 1ea, Classification 2ea, Segmentation 2ea)',
          runnerHighlight: 'Challenging Case: 180장(4128x2000) 추론 8초 이내',
          runnerNotes: ['기존 추론 방식 대비 96.0% 속도 개선 (120.5s → 4.8s)', 'Runner를 통한 추론 속도 개선 사례'],
          imagePath: '/assets/cases/usecase_MX.jpg',
        },
        {
          title: 'VD 세트 외관 검사',
          category: 'Assembly Inspection',
          defectNote: '스크래치, 찍힘, 갭 등 다유형의 불량 검출 필요',
          trainerModels: '5종 AI 모델 (Classification 4ea, Segmentation 1ea)',
          runnerHighlight: 'Challenging Case: 약 400장(384x384) 추론 3초 이내',
          runnerNotes: ['라벨링-학습-배포-추론 End-to-End MLOps 파이프라인 구축', 'DICE 기반 AI 검사 Lifecycle 통합 운영 사례'],
          imagePath: '/assets/cases/usecase_VD.png',
        },
      ],
    },
    environment: {
      eyebrow: 'OPERATION',
      title: '내부 환경에서 운영',
      lead: 'DICE는 외부 툴에 데이터를 흩어두지 않고 사내 실행 환경 안에서 AI 검사 흐름을 연결합니다.',
      points: [
        {
          title: 'Kubernetes 배포',
          description: 'Labeler, Platform, Runner를 서비스 단위로 분리해 운영합니다.',
        },
        {
          title: 'Istio 라우팅',
          description: '도메인과 경로 기준으로 각 제품 화면과 API를 연결합니다.',
        },
        {
          title: '내부 GPU 활용',
          description: '학습 Job을 사내 GPU 자원과 연결해 모델을 생성합니다.',
        },
        {
          title: 'Runner 실행',
          description: '학습 모델을 현장 추론 환경에서 사용할 수 있도록 준비합니다.',
        },
      ],
    },
    cta: {
      title: 'DICE로 제조 검사 AI를 운영하세요',
      lead: '데이터셋부터 현장 실행까지 같은 제품 흐름 안에서 관리합니다.',
      primary: '빠른 시작',
      secondary: '가이드 보기',
    },
    footer: 'DICE Vision AI Platform',
    ui: {
      dataset: 'Dataset',
      training: 'Training Job',
      runner: 'Runner',
      mediaPhoto: 'PHOTO',
      mediaVideo: 'VIDEO',
      assetReady: 'Asset slot',
      metric: 'Metric',
      model: 'Model',
      status: 'Status',
      complete: 'Completed',
      live: 'Live',
      previous: '이전 사례',
      next: '다음 사례',
    },
  },
  en: {
    nav: {
      links: [
        { label: 'Defect', href: '/defect' },
        { label: 'Labeler', href: '/labeler' },
        { label: 'Trainer', href: '/platform' },
        { label: 'Runner', href: '/runner' },
        { label: 'Docs', href: '/docs/en/guide/overview' },
        { label: 'Download', href: '/downloads' },
        { label: 'Activation', href: '/activation' },
      ],
      start: 'Start',
    },
    hero: {
      eyebrow: 'DICE Vision AI Suite',
      titleTop: 'Platform for',
      titleMain: 'Manufacturing AI Inspection',
      lead: 'Dataset, training, and runtime platform for manufacturing inspection AI',
      primary: 'Start',
      secondary: 'Docs',
    },
    proof: [
      { value: 'Label', label: 'Annotation and review' },
      { value: 'Train', label: 'Training metrics' },
      { value: 'Export', label: 'Model conversion' },
      { value: 'Run', label: 'On-site inference' },
    ],
    labelerTrainer: {
      badge: 'DICE-Labeler/Trainer',
      taglines: ['AI training data labeling solution: Labeler', 'AI training platform solution: Trainer'],
      sectionTitle: 'Manage inspection AI model development in one place',
      sectionSubtitle: 'End-to-end AI vision workflow from data management to training, deployment, and inference',
      flow: [
        { title: 'Labeling', description: 'Create training data with an intuitive labeling tool' },
        { title: 'Train', description: 'Support diverse models for your inspection goals and conditions' },
        { title: 'Analysis', description: 'Verify the performance of trained models' },
        { title: 'Export', description: 'Model export and export history management' },
      ],
      features: [
        {
          title: 'Easy training / labeling',
          bullets: ['Intuitive training and labeling, no AI expertise required', 'Complete a vision inspection model in just a few clicks'],
        },
        {
          title: 'High accuracy / performance',
          bullets: ['AI model training optimized for accurate defect detection', 'Continuously improve inspection quality with data-driven training'],
        },
        {
          title: 'Fast model creation / deployment',
          bullets: ['Maximize field responsiveness with fast training cycles', 'Shorten development time and speed up production deployment'],
        },
        {
          title: 'Robust model training',
          bullets: ['Handle real-world data constraints such as class imbalance', 'Support stable model training even with limited data'],
        },
      ],
    },
    runner: {
      badge: 'DICE-Runner',
      taglines: ['AI inspection high-performance inference solution: Runner'],
      sectionTitle: 'Apply inspection AI models directly to inspection',
      sectionSubtitle: 'End-to-end AI vision workflow from deployment to inference and operations management',
      flow: [
        { title: 'Model', description: 'Manage registered models and versions', image: '/assets/screens/runner_model.png' },
        { title: 'Deploy', description: 'Deploy AI models suited to your inference environment', image: '/assets/screens/runner_deploy.jpg' },
        { title: 'Inference', description: 'Stable inference at scale, with inference simulation support', image: '/assets/screens/runner_inference.png' },
        { title: 'Monitoring', description: 'Stable PC status and model monitoring in production', image: '/assets/screens/runner_monitoring.png' },
      ],
      features: [
        {
          title: 'High-speed inference / high throughput',
          bullets: ['Real-time inspection with multi-worker parallel inference', 'Fast response and high throughput via GPU/CPU optimization'],
        },
        {
          title: 'Easy model deployment',
          bullets: ['Simple deployment across model types for any inspection setup', 'Fast model swaps and easy model scaling'],
        },
        {
          title: 'Easy system integration',
          bullets: ['Simple integration with inspection systems via REST API', 'Fast, flexible AI deployment across manufacturing environments'],
        },
        {
          title: 'Stable AI service operation',
          bullets: ['Monitor inference performance and service status', 'Sustain AI inspection quality and operational stability'],
        },
      ],
    },
    cases: {
      eyebrow: 'USE CASES',
      title: 'Applied Cases',
      lead: 'Real-world cases of AI-based vision inspection in production.',
      items: [
        {
          title: 'MX Metal Surface Inspection',
          category: 'Surface Inspection',
          defectNote: 'Requires detecting scratches, dents, stains, white spots, and segment discoloration',
          trainerModels: '5 AI models (Detection x1, Classification x2, Segmentation x2)',
          runnerHighlight: 'Challenging Case: 180 images (4128x2000), inference within 8 seconds',
          runnerNotes: ['96.0% speed improvement over the previous inference method (120.5s → 4.8s)', 'Inference speed improvement case via Runner'],
          imagePath: '/assets/cases/usecase_MX.jpg',
        },
        {
          title: 'VD Assembly Surface Inspection',
          category: 'Assembly Inspection',
          defectNote: 'Requires detecting scratches, dents, and gaps',
          trainerModels: '5 AI models (Classification x4, Segmentation x1)',
          runnerHighlight: 'Challenging Case: about 400 images (384x384), inference within 3 seconds',
          runnerNotes: ['Built an end-to-end MLOps pipeline covering labeling, training, deployment, and inference', 'Integrated AI inspection lifecycle operation case powered by DICE'],
          imagePath: '/assets/cases/usecase_VD.png',
        },
      ],
    },
    environment: {
      eyebrow: 'OPERATION',
      title: 'Operates Inside Your Environment',
      lead: 'DICE keeps the inspection AI workflow connected inside the company execution environment.',
      points: [
        {
          title: 'Kubernetes deployment',
          description: 'Operate Labeler, Platform, and Runner as separated services.',
        },
        {
          title: 'Istio routing',
          description: 'Connect product screens and APIs by domain and route.',
        },
        {
          title: 'Internal GPU',
          description: 'Run training jobs against internal GPU resources.',
        },
        {
          title: 'Runner execution',
          description: 'Prepare trained models for field inference runtime.',
        },
      ],
    },
    cta: {
      title: 'Operate manufacturing inspection AI with DICE',
      lead: 'Keep datasets, training, and field runtime in one product flow.',
      primary: 'Quick start',
      secondary: 'Read guide',
    },
    footer: 'DICE Vision AI Platform',
    ui: {
      dataset: 'Dataset',
      training: 'Training Job',
      runner: 'Runner',
      mediaPhoto: 'PHOTO',
      mediaVideo: 'VIDEO',
      assetReady: 'Asset slot',
      metric: 'Metric',
      model: 'Model',
      status: 'Status',
      complete: 'Completed',
      live: 'Live',
      previous: 'Previous case',
      next: 'Next case',
    },
  },
};

export default function LandingPage({ lang = 'ko', isAuthenticated, userName, onLogin, onLogout }: LandingPageProps) {
  const dashboardHref = useDashboardLink(!!isAuthenticated, userName);
  const content = CONTENT[lang] ?? CONTENT.ko;
  const [activeCase, setActiveCase] = React.useState(0);
  const [userMenuOpen, setUserMenuOpen] = React.useState(false);
  const caseRailRef = React.useRef<HTMLDivElement | null>(null);
  const userMenuRef = React.useRef<HTMLDivElement | null>(null);

  const userInitials = React.useMemo(() => {
    const raw = (userName || '').trim();
    if (!raw) return 'U';
    const local = raw.includes('@') ? raw.split('@')[0] : raw;
    const parts = local.split(/[.\-_\s]+/).filter(Boolean);
    const letters = parts.length >= 2 ? parts[0][0] + parts[1][0] : local.slice(0, 2);
    return letters.toUpperCase();
  }, [userName]);

  React.useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const  MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  React.useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }

    const nodes = Array.from(document.querySelectorAll<HTMLElement>('.dice-reveal'));
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
          }
        });
      },
      { threshold: 0.16 },
    );

    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, []);

  const scrollToCase = (index: number) => {
    const rail = caseRailRef.current;
    const item = rail?.children[index] as HTMLElement | undefined;
    item?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    setActiveCase(index);
  };

  const handleCaseScroll = () => {
    const rail = caseRailRef.current;
    if (!rail) {
      return;
    }

    const children = Array.from(rail.children) as HTMLElement[];
    const railCenter = rail.scrollLeft + rail.clientWidth / 2;
    const nearest = children.reduce(
      (best, child, index) => {
        const childCenter = child.offsetLeft + child.offsetWidth / 2;
        const distance = Math.abs(childCenter - railCenter);
        return distance < best.distance ? { index, distance } : best;
      },
      { index: 0, distance: Number.POSITIVE_INFINITY },
    );
    setActiveCase(nearest.index);
  };

  const signalContent = SIGNAL_CONTENT[lang];

  return (
    <div className="dice-landing">
      <style dangerouslySetInnerHTML={{ __html: styles }} suppressHydrationWarning />

      <header className="dice-header">
        <div className="dice-brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="dice-brand-mark" src={withBasePath('/dice_icon.png')} alt="" aria-hidden="true" />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="dice-brand-word" src={withBasePath('/dice-lettermark.png')} alt="DICE" />
        </div>
        <nav className="dice-nav">
          {withDashboardLink(content.nav.links, dashboardHref).map((link, index, list) => (
            <React.Fragment key={link.label}>
              <a href={link.href}>{link.label}</a>
              {link.label === 'Defect' && index < list.length - 1 ? (
                <span className="dice-nav-divider" aria-hidden="true" />
              ) : null}
            </React.Fragment>
          ))}
        </nav>
        <div className="dice-header-actions">
          {isAuthenticated ? (
            <div className="dice-user" ref={userMenuRef}>
              <button
                type="button"
                className="dice-user-badge"
                aria-haspopup="menu"
                aria-expanded={userMenuOpen}
                title={userName ?? undefined}
                 => setUserMenuOpen((v) => !v)}
              >
                {userInitials}
              </button>
              {userMenuOpen ? (
                <div className="dice-user-menu" role="menu">
                  <div className="dice-user-menu-id">{userName}</div>
                  <a href="/settings" className="dice-user-menu-item" role="menuitem">
                    설정
                  </a>
                  <button
                    type="button"
                    className="dice-user-menu-item danger"
                    role="menuitem"
                     => {
                      setUserMenuOpen(false);
                      onLogout?.();
                    }}
                  >
                    로그아웃
                  </button>
                </div>
              ) : null}
            </div>
          ) : (
            <button
              
              className="dice-start-button"
              type="button"
            >
              로그인
            </button>
          )}
        </div>
      </header>

      <main>
        <section className="dice-hero" id="top">
          <div className="dice-section-inner dice-hero-grid">
            <div className="dice-hero-copy dice-reveal">
              <p className="dice-eyebrow dark">{content.hero.eyebrow}</p>
              <h1>
                <span>{content.hero.titleTop}</span>
                {content.hero.titleMain}
              </h1>
              <p className="dice-hero-lead">{content.hero.lead}</p>
              <div className="dice-hero-actions">
                <a className="dice-primary-link" href="/platform">
                  {content.hero.primary}
                  <span aria-hidden="true">></span>
                </a>
                <a className="dice-secondary-link" href={lang === 'ko' ? '/docs/ko/guide/overview' : '/docs/en/guide/overview'}>
                  {content.hero.secondary}
                </a>
              </div>
            </div>

            <div className="dice-reveal delay-1">
              <HeroConsole content={content} />
            </div>
          </div>

          <div className="dice-section-inner dice-proof dice-reveal delay-2" aria-label="DICE workflow summary">
            {content.proof.map((point) => (
              <div key={point.value} className="dice-proof-item">
                <strong>{point.value}</strong>
                <span>{point.label}</span>
              </div>
            ))}
          </div>
        </section>

        <SignalSection content={signalContent} />

        <ModuleSection module={content.labelerTrainer} id="suite" previewImage="/assets/screens/platform-training-metrics.png" />

        <ModuleSection module={content.runner} id="runner" previewImage="/assets/screens/runner_main.png" />

        <section className="dice-section dice-cases" id="cases">
          <div className="dice-section-inner">
            <SectionHeading eyebrow={content.cases.eyebrow} title={content.cases.title} lead={content.cases.lead} />

            <div className="dice-case-shell dice-reveal">
              <div className="dice-case-rail" ref={caseRailRef} >
                {content.cases.items.map((item, index) => (
                  <article className="dice-case-card" key={item.title}>
                    <div className="dice-case-copy">
                      <span>{item.category}</span>
                      <h3>{item.title}</h3>
                      <p className="dice-case-defect">{item.defectNote}</p>
                      <div className="dice-case-split">
                        <div>
                          <strong>Trainer</strong>
                          <span>{item.trainerModels}</span>
                        </div>
                        <div>
                          <strong>Runner</strong>
                          <span>{item.runnerHighlight}</span>
                          <ul>
                            {item.runnerNotes.map((note) => (
                              <li key={note}>{note}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                    {item.imagePath ? (
                      /* eslint-disable-next-line @next/next/no-img-element */
                      <img src={withBasePath(item.imagePath)} alt={item.title} className="dice-case-image" />
                    ) : (
                      <MediaSlot label={content.ui.mediaPhoto} tone={index} />
                    )}
                  </article>
                ))}
              </div>

              <div className="dice-case-controls">
                <button
                  aria-label={content.ui.previous}
                   => scrollToCase(Math.max(activeCase - 1, 0))}
                  type="button"
                >
                  <
                </button>
                <div className="dice-case-dots" aria-label="Case pagination">
                  {content.cases.items.map((item, index) => (
                    <button
                      aria-label={`${item.title} ${index + 1}`}
                      className={index === activeCase ? 'active' : ''}
                      key={item.title}
                       => scrollToCase(index)}
                      type="button"
                    />
                  ))}
                </div>
                <button
                  aria-label={content.ui.next}
                   => scrollToCase(Math.min(activeCase + 1, content.cases.items.length - 1))}
                  type="button"
                >
                  >
                </button>
              </div>
            </div>
          </div>
        </section>

        <section className="dice-cta">
          <div className="dice-section-inner dice-cta-inner dice-reveal">
            <h2>{content.cta.title}</h2>
            <p>{content.cta.lead}</p>
            <div className="dice-hero-actions">
              <a className="dice-primary-link" href="/platform">
                {content.cta.primary}
                <span aria-hidden="true">-></span>
              </a>
              <a className="dice-secondary-link" href={lang === 'ko' ? '/docs/ko/guide/overview' : '/docs/en/guide/overview'}>
                {content.cta.secondary}
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className="dice-footer">
        <div className="dice-section-inner">
          <span>{content.footer}</span>
          <a href="#top">Top</a>
        </div>
      </footer>
    </div>
  );
}

function SignalSection({ content }: { content: SignalContent }) {
  return (
    <section className="dice-signal-section" aria-label={content.title}>
      <div className="dice-section-inner dice-signal-grid">
        <div className="dice-signal-copy dice-reveal">
          <p className="dice-eyebrow">{content.eyebrow}</p>
          <h2>{content.title}</h2>
          <p>{content.lead}</p>

          <div className="dice-flow-compare" aria-label="Traditional inspection AI workflow compared with DICE">
            <div>
              <span>{content.beforeTitle}</span>
              {content.before.map((item) => (
                <article key={item.title}>
                  <strong>{item.title}</strong>
                  <p>{item.description}</p>
                </article>
              ))}
            </div>
            <div className="after">
              <span>{content.afterTitle}</span>
              {content.after.map((item) => (
                <article key={item.title}>
                  <strong>{item.title}</strong>
                  <p>{item.description}</p>
                </article>
              ))}
            </div>
          </div>
        </div>

        <div className="dice-signal-board dice-reveal delay-1">
          <div className="dice-flow-board" aria-label="DICE workflow improvement map">
            <div className="dice-flow-lane old">
              <span>{content.beforeTitle}</span>
              <div className="dice-flow-lane-nodes">
                {content.beforeFlow.map((step, index) => (
                  <div className="dice-flow-node compact" key={step}>
                    <small>{String(index + 1).padStart(2, '0')}</small>
                    <strong>{step}</strong>
                  </div>
                ))}
              </div>
            </div>

            <div className="dice-flow-lane new">
              <span>{content.afterTitle}</span>
              <div className="dice-flow-lane-nodes">
                {content.afterFlow.map((step, index) => (
                  <React.Fragment key={step}>
                    <div className="dice-flow-node active">
                      <small>{String(index + 1).padStart(2, '0')}</small>
                      <strong>{step}</strong>
                    </div>
                    {index < content.afterFlow.length - 1 ? <div className="dice-flow-axis" aria-hidden="true" /> : null}
                  </React.Fragment>
                ))}
              </div>
            </div>
          </div>

          <div className="dice-signal-stats">
            {content.outcomes.map((stat) => (
              <div className="dice-signal-stat" key={stat.label}>
                <strong>{stat.value}</strong>
                <span>{stat.label}</span>
                <p>{stat.caption}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function SectionHeading({ eyebrow, title, lead }: { eyebrow: string; title: string; lead: string }) {
  return (
    <div className="dice-section-heading dice-reveal">
      <p className="dice-eyebrow">{eyebrow}</p>
      <h2>{title}</h2>
      <p>{lead}</p>
    </div>
  );
}

function HeroConsole({ content }: { content: Content }) {
  return (
    <div className="dice-hero-console" aria-label="DICE product preview">
      <div className="dice-console-top">
        <span>DICE Platform</span>
        <strong>{content.ui.live}</strong>
      </div>
      <div className="dice-console-body">
        <div className="dice-console-sidebar">
          <strong>{content.ui.dataset}</strong>
          {['metal-final', 'pcb-solder', 'camera-module', 'battery-cell'].map((item, index) => (
            <span className={index === 0 ? 'active' : ''} key={item}>
              {item}
            </span>
          ))}
        </div>
        <div className="dice-console-media">
          <MediaSlot label={content.ui.mediaPhoto} tone={1} compact />
        </div>
        <div className="dice-console-metrics">
          <strong>{content.ui.training}</strong>
          <MiniChart />
          <div className="dice-metric-row">
            <span>mAP50</span>
            <b>99.50%</b>
          </div>
          <div className="dice-metric-row">
            <span>{content.ui.status}</span>
            <b>{content.ui.complete}</b>
          </div>
        </div>
      </div>
    </div>
  );
}

function ModuleSection({ module, id, previewImage }: { module: ProductModule; id: string; previewImage: string }) {
  return (
    <section className="dice-section dice-module" id={id}>
      <div className="dice-section-inner">
        <div className="dice-module-header dice-reveal">
          <div className="dice-module-header-copy">
            <h3>{module.badge}</h3>
            {module.taglines.map((line) => (
              <p key={line}>{line}</p>
            ))}
          </div>
          <div className="dice-module-header-media">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt={module.badge} className="dice-module-header-image" src={withBasePath(previewImage)} />
          </div>
        </div>

        <div className="dice-module-body dice-reveal delay-1">
          <div className="dice-module-intro">
            <h2>{module.sectionTitle}</h2>
            <p>{module.sectionSubtitle}</p>
          </div>

          <div className="dice-module-flow">
            {module.flow.map((step, index) => (
              <React.Fragment key={step.title}>
                <article className="dice-module-flow-step">
                  <span className="dice-module-flow-badge">{step.title}</span>
                  <p>{step.description}</p>
                  {step.image ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img src={withBasePath(step.image)} alt={step.title} className="dice-module-flow-image" />
                  ) : (
                    <MediaSlot label={index % 2 === 0 ? 'PHOTO' : 'SCREEN'} tone={index} compact />
                  )}
                </article>
                {index < module.flow.length - 1 ? (
                  <div className="dice-module-flow-arrow" aria-hidden="true">
                    >
                  </div>
                ) : null}
              </React.Fragment>
            ))}
          </div>

          <div className="dice-module-features">
            {module.features.map((feature, index) => (
              <article className="dice-module-feature" key={feature.title}>
                <span className="dice-card-number">{String(index + 1).padStart(2, '0')}</span>
                <h3>{feature.title}</h3>
                <ul>
                  {feature.bullets.map((bullet) => (
                    <li key={bullet}>{bullet}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function MediaSlot({ label, tone, compact = false }: { label: string; tone: number; compact?: boolean }) {
  return (
    <div className={`dice-media-slot tone-${tone} ${compact ? 'compact' : ''}`} aria-label={label}>
      <span>{label}</span>
      <i />
    </div>
  );
}

function MiniChart({ variant = 'metric' }: { variant?: 'metric' | 'loss' }) {
  const metricPath = 'M8 82 L24 38 L42 24 L60 30 L78 20 L100 24 L122 18 L146 19 L170 17 L194 18 L218 16';
  const lossPath = 'M8 18 L22 78 L38 62 L54 70 L70 58 L90 66 L112 64 L136 74 L164 79 L190 84 L218 88';

  return (
    <svg className="dice-mini-chart" viewBox="0 0 226 104" role="img" aria-label={`${variant} chart`}>
      <path d="M8 24 H218 M8 48 H218 M8 72 H218 M8 96 H218" className="grid" />
      {variant === 'metric' ? (
        <>
          <path d="M8 88 L24 56 L42 38 L60 44 L78 32 L100 36 L122 28 L146 30 L170 24 L194 22 L218 18" className="accent" />
          <path d={metricPath} className="success" />
        </>
      ) : (
        <path d={lossPath} className="accent" />
      )}
    </svg>
  );
}

const styles = `
  :root {
    color-scheme: light;
  }

  html {
    scroll-behavior: smooth;
  }

  .dice-landing {
    --bg: #f3f6fb;
    --surface: #ffffff;
    --surface-soft: #eef4fb;
    --ink: #101827;
    --muted: #526176;
    --line: #d8e1ee;
    --line-strong: #b8c7da;
    --primary: #1f3fbd;
    --primary-dark: #172f93;
    --cyan: #00c8b8;
    --green: #16a36c;
    --orange: #f59e0b;
    --red: #ef4444;
    --dark: #07111f;
    --dark-soft: #101c2c;
    --shadow: 0 22px 60px rgba(15, 23, 42, 0.14);
    background: var(--bg);
    color: var(--ink);
    font-family:
      Inter,
      Pretendard,
      -apple-system,
      BlinkMacSystemFont,
      "Segoe UI",
      sans-serif;
    letter-spacing: 0;
    min-height: 100vh;
    overflow-wrap: break-word;
    word-break: keep-all;
  }

  .dice-landing *,
  .dice-landing *::before,
  .dice-landing *::after {
    box-sizing: border-box;
  }

  .dice-landing a {
    color: inherit;
    text-decoration: none;
  }

  .dice-header {
    align-items: center;
    background: rgba(255, 255, 255, 0.94);
    border-bottom: 1px solid var(--line);
    display: flex;
    gap: 28px;
    height: 64px;
    justify-content: space-between;
    left: 0;
    padding: 0 48px;
    position: sticky;
    right: 0;
    top: 0;
    z-index: 20;
  }

  .dice-brand {
    align-items: center;
    color: var(--primary);
    display: inline-flex;
    font-size: 18px;
    font-weight: 850;
    gap: 10px;
    letter-spacing: 0;
    white-space: nowrap;
  }

  .dice-brand-mark {
    display: inline-flex;
    height: 32px;
    width: 32px;
    object-fit: contain;
  }

  .dice-brand-word {
    display: inline-block;
    height: 30px;
    width: auto;
    object-fit: contain;
  }

  .dice-nav {
    align-items: center;
    display: flex;
    gap: 26px;
    justify-content: center;
    margin-left: auto;
  }

  .dice-nav a {
    color: #334155;
    font-size: 15px;
    font-weight: 700;
    line-height: 1;
  }

  .dice-nav a:hover {
    color: var(--primary);
  }

  .dice-nav-divider {
    align-self: stretch;
    background: #cbd5e1;
    flex-shrink: 0;
    margin: 2px 0;
    width: 1px;
  }

  .dice-header-actions {
    align-items: center;
    display: flex;
    gap: 14px;
  }

  .dice-user {
    position: relative;
  }

  .dice-user-badge {
    align-items: center;
    background: var(--primary);
    border: 0;
    border-radius: 999px;
    color: #fff;
    cursor: pointer;
    display: inline-flex;
    font-size: 13px;
    font-weight: 800;
    height: 38px;
    justify-content: center;
    letter-spacing: 0.3px;
    transition: transform 160ms ease, box-shadow 160ms ease;
    width: 38px;
  }

  .dice-user-badge:hover {
    box-shadow: 0 4px 14px rgba(31, 63, 189, 0.35);
    transform: translateY(-1px);
  }

  .dice-user-menu {
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 12px;
    box-shadow: 0 18px 44px rgba(15, 23, 42, 0.16);
    min-width: 200px;
    overflow: hidden;
    padding: 6px;
    position: absolute;
    right: 0;
    top: calc(100% + 10px);
    z-index: 30;
  }

  .dice-user-menu-id {
    color: #64748b;
    font-size: 12px;
    font-weight: 700;
    overflow: hidden;
    padding: 8px 12px 10px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dice-user-menu-item {
    background: transparent;
    border: 0;
    border-radius: 8px;
    color: #334155;
    cursor: pointer;
    display: block;
    font-size: 14px;
    font-weight: 700;
    padding: 10px 12px;
    text-align: left;
    text-decoration: none;
    width: 100%;
  }

  .dice-user-menu-item:hover {
    background: #eef2fb;
  }

  .dice-user-menu-item.danger {
    color: #dc2626;
  }

  .dice-user-menu-item.danger:hover {
    background: #fef2f2;
  }

  .dice-language {
    align-items: center;
    background: #edf2f8;
    border: 1px solid var(--line);
    border-radius: 999px;
    display: inline-flex;
    padding: 3px;
  }

  .dice-language a {
    align-items: center;
    border-radius: 999px;
    color: #475569;
    display: inline-flex;
    font-size: 12px;
    font-weight: 800;
    height: 24px;
    justify-content: center;
    width: 38px;
  }

  .dice-language a.active {
    background: var(--primary);
    color: #fff;
  }

  .dice-start-button,
  .dice-primary-link,
  .dice-secondary-link {
    align-items: center;
    border-radius: 999px;
    display: inline-flex;
    font-size: 15px;
    font-weight: 850;
    justify-content: center;
    min-height: 48px;
    padding: 0 26px;
    transition:
      transform 180ms ease,
      background 180ms ease,
      border-color 180ms ease;
    white-space: nowrap;
  }

  .dice-start-button,
  .dice-primary-link {
    background: var(--primary);
    color: #fff;
  }

  .dice-start-button {
    min-height: 44px;
    padding: 0 22px;
  }

  .dice-primary-link:hover,
  .dice-start-button:hover,
  .dice-secondary-link:hover {
    transform: translateY(-2px);
  }

  .dice-primary-link span {
    margin-left: 10px;
  }

  .dice-secondary-link {
    border: 1px solid rgba(255, 255, 255, 0.28);
    color: #fff;
  }

  .dice-section-inner {
    margin: 0 auto;
    max-width: 1180px;
    width: calc(100% - 96px);
  }

  .dice-section {
    padding: 96px 0;
  }

  .dice-hero {
    background:
      linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px),
      linear-gradient(0deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px),
      linear-gradient(135deg, #0a1b3d 0%, #112b64 54%, #063b43 100%);
    background-size:
      32px 32px,
      32px 32px,
      auto;
    color: #fff;
    overflow: hidden;
    padding: 88px 0 72px;
    position: relative;
  }

  .dice-hero::after {
    background: linear-gradient(120deg, transparent, rgba(255, 255, 255, 0.08), transparent);
    content: "";
    height: 1px;
    left: 8%;
    position: absolute;
    right: 8%;
    top: 34%;
    transform: rotate(-12deg);
  }

  .dice-hero-grid {
    align-items: center;
    display: grid;
    gap: 52px;
    grid-template-columns: 0.92fr 1.08fr;
    position: relative;
    z-index: 1;
  }

  .dice-eyebrow {
    color: var(--primary);
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 0;
    margin: 0 0 14px;
    text-transform: uppercase;
  }

  .dice-eyebrow.dark {
    align-items: center;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 999px;
    color: #dce7ff;
    display: inline-flex;
    margin-bottom: 22px;
    padding: 8px 13px;
  }

  .dice-eyebrow.dark::before {
    background: var(--cyan);
    border-radius: 50%;
    content: "";
    height: 7px;
    margin-right: 8px;
    width: 7px;
  }

  .dice-eyebrow.light {
    color: #76fff1;
  }

  .dice-hero h1 {
    color: #dbe8ff;
    font-size: 64px;
    font-weight: 900;
    letter-spacing: 0;
    line-height: 1.05;
    margin: 0;
  }

  .dice-hero h1 span {
    color: #c7d8f8;
    display: block;
    font-size: 30px;
    margin-bottom: 14px;
  }

  .dice-hero-lead {
    color: #d8e3f8;
    font-size: 20px;
    font-weight: 650;
    line-height: 1.65;
    margin: 26px 0 0;
    max-width: 560px;
  }

  .dice-hero-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    margin-top: 34px;
  }

  .dice-hero .dice-primary-link {
    background: #fff;
    color: var(--primary);
  }

  .dice-hero-console {
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.6);
    border-radius: 8px;
    box-shadow: 0 26px 70px rgba(2, 8, 23, 0.22);
    color: var(--ink);
    overflow: hidden;
    position: relative;
    transform: perspective(1200px) rotateY(-2deg) rotateX(1deg);
    transform-origin: center right;
  }

  .dice-hero-console::before {
    background: linear-gradient(90deg, var(--cyan), var(--primary), #7c3aed);
    content: "";
    height: 3px;
    left: 0;
    position: absolute;
    right: 0;
    top: 0;
    z-index: 2;
  }

  .dice-hero-console::after {
    background: linear-gradient(135deg, transparent 0 58%, rgba(31, 63, 189, 0.08) 58% 100%);
    bottom: 0;
    content: "";
    pointer-events: none;
    position: absolute;
    right: 0;
    top: 0;
    width: 46%;
  }

  .dice-console-top {
    align-items: center;
    background: rgba(255, 255, 255, 0.86);
    border-bottom: 1px solid rgba(216, 225, 238, 0.8);
    display: flex;
    justify-content: space-between;
    min-height: 62px;
    padding: 0 18px;
    position: relative;
    z-index: 1;
  }

  .dice-console-top span {
    font-size: 15px;
    font-weight: 900;
  }

  .dice-console-top strong {
    background: #e7f8ef;
    border-radius: 999px;
    color: #047857;
    font-size: 12px;
    font-weight: 850;
    padding: 6px 10px;
  }

  .dice-console-body {
    display: grid;
    grid-template-columns: 150px minmax(230px, 1fr) 190px;
    min-height: 350px;
  }

  .dice-console-sidebar {
    background: var(--dark);
    color: #cbd5e1;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 20px 14px;
  }

  .dice-console-sidebar strong {
    color: #fff;
    font-size: 13px;
    margin-bottom: 4px;
  }

  .dice-console-sidebar span {
    border-radius: 6px;
    font-size: 12px;
    font-weight: 750;
    overflow: hidden;
    padding: 10px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dice-console-sidebar span.active {
    background: #1b2a40;
    color: #fff;
  }

  .dice-console-media {
    align-items: center;
    background:
      linear-gradient(120deg, #edf3fa 0%, #f8fbff 52%, #e8eff8 100%);
    display: flex;
    justify-content: center;
    padding: 24px;
  }

  .dice-console-metrics {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 22px 18px;
  }

  .dice-console-metrics > strong {
    font-size: 13px;
  }

  .dice-metric-row {
    align-items: center;
    border-top: 1px solid var(--line);
    display: flex;
    font-size: 12px;
    justify-content: space-between;
    padding-top: 12px;
  }

  .dice-metric-row span {
    color: var(--muted);
    font-weight: 750;
  }

  .dice-metric-row b {
    color: var(--primary);
  }

  .dice-proof {
    background: rgba(255, 255, 255, 0.06);
    border-bottom: 1px solid rgba(255, 255, 255, 0.16);
    border-top: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 0;
    display: grid;
    gap: 0;
    grid-template-columns: repeat(4, 1fr);
    margin-top: 54px;
    overflow: hidden;
    position: relative;
    z-index: 1;
  }

  .dice-proof-item {
    background: transparent;
    border-left: 1px solid rgba(255, 255, 255, 0.14);
    min-height: 92px;
    padding: 20px;
  }

  .dice-proof-item:first-child {
    border-left: 0;
  }

  .dice-proof-item strong {
    color: #fff;
    display: block;
    font-size: 25px;
    line-height: 1;
  }

  .dice-proof-item span {
    color: #c8d5eb;
    display: block;
    font-size: 13px;
    font-weight: 750;
    margin-top: 10px;
  }

  .dice-signal-section {
    background: #fff;
    padding: 72px 0 104px;
    position: relative;
  }

  .dice-signal-section::before {
    background: var(--bg);
    content: "";
    height: 92px;
    left: 0;
    position: absolute;
    right: 0;
    top: 0;
  }

  .dice-signal-grid {
    align-items: stretch;
    display: grid;
    gap: 30px;
    grid-template-columns: 0.84fr 1.16fr;
    position: relative;
    z-index: 2;
  }

  .dice-signal-copy {
    background: #fff;
    border-top: 3px solid var(--primary);
    box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
    padding: 34px 34px 30px;
  }

  .dice-signal-copy h2 {
    font-size: 34px;
    line-height: 1.2;
    margin: 0;
  }

  .dice-signal-copy > p:last-of-type {
    color: var(--muted);
    font-size: 16px;
    line-height: 1.72;
    margin: 16px 0 0;
  }

  .dice-flow-compare {
    border: 1px solid var(--line);
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-top: 30px;
  }

  .dice-flow-compare > div {
    padding: 22px;
  }

  .dice-flow-compare > div + div {
    border-left: 1px solid var(--line);
  }

  .dice-flow-compare .after {
    background: #f8fbff;
  }

  .dice-flow-compare span {
    color: var(--primary);
    display: block;
    font-size: 12px;
    font-weight: 900;
    margin-bottom: 16px;
    text-transform: uppercase;
  }

  .dice-flow-compare article + article {
    border-top: 1px solid var(--line);
    margin-top: 16px;
    padding-top: 16px;
  }

  .dice-flow-compare strong {
    color: var(--ink);
    display: block;
    font-size: 15px;
    line-height: 1.35;
  }

  .dice-flow-compare article p {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.55;
    margin: 7px 0 0;
  }

  .dice-industry-wall {
    border-bottom: 1px solid var(--line);
    border-top: 1px solid var(--line);
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-top: 28px;
  }

  .dice-industry-wall span {
    border-left: 1px solid var(--line);
    color: #334155;
    font-size: 13px;
    font-weight: 850;
    min-height: 48px;
    padding: 15px 14px;
  }

  .dice-industry-wall span:nth-child(2n + 1) {
    border-left: 0;
  }

  .dice-industry-wall span:nth-child(n + 3) {
    border-top: 1px solid var(--line);
  }

  .dice-signal-board {
    background:
      linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px),
      linear-gradient(0deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px),
      #07111f;
    background-size: 32px 32px;
    box-shadow: 0 28px 70px rgba(2, 8, 23, 0.22);
    color: #fff;
    overflow: hidden;
    padding: 30px;
    position: relative;
  }

  .dice-signal-board::after {
    background: linear-gradient(135deg, transparent 0 56%, rgba(0, 200, 184, 0.14) 56% 100%);
    bottom: 0;
    content: "";
    pointer-events: none;
    position: absolute;
    right: 0;
    top: 0;
    width: 52%;
  }

  .dice-signal-map,
  .dice-system-ribbon,
  .dice-signal-stats {
    position: relative;
    z-index: 1;
  }

  .dice-flow-board {
    display: grid;
    gap: 24px;
    position: relative;
    z-index: 1;
  }

  .dice-flow-lane {
    border: 1px solid rgba(255, 255, 255, 0.16);
    padding: 22px;
  }

  .dice-flow-lane.old {
    background: rgba(255, 255, 255, 0.04);
    opacity: 0.72;
  }

  .dice-flow-lane.new {
    background: rgba(31, 63, 189, 0.24);
    border-color: rgba(118, 255, 241, 0.36);
  }

  .dice-flow-lane > span {
    color: #76fff1;
    display: block;
    font-size: 12px;
    font-weight: 900;
    margin-bottom: 16px;
    text-transform: uppercase;
  }

  .dice-flow-lane-nodes {
    align-items: stretch;
    display: grid;
    gap: 14px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .dice-flow-lane.old .dice-flow-lane-nodes {
    gap: 8px;
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }

  .dice-flow-lane.new .dice-flow-lane-nodes {
    align-items: center;
    gap: 0;
    grid-template-columns: 1fr 34px 1fr 34px 1fr;
  }

  .dice-flow-node {
    align-items: flex-start;
    border: 1px solid rgba(255, 255, 255, 0.18);
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 88px;
    padding: 16px;
  }

  .dice-flow-node.active {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(118, 255, 241, 0.5);
  }

  .dice-flow-node.compact {
    min-height: 78px;
    padding: 12px 10px;
  }

  .dice-flow-node small {
    color: #76fff1;
    font-size: 11px;
    font-weight: 900;
    margin-bottom: 14px;
  }

  .dice-flow-node.compact small {
    color: #94a3b8;
    margin-bottom: 10px;
  }

  .dice-flow-node strong {
    color: #fff;
    font-size: 16px;
    line-height: 1.25;
  }

  .dice-flow-node.compact strong {
    color: #cbd5e1;
    font-size: 12px;
    line-height: 1.32;
  }

  .dice-flow-axis {
    background: rgba(118, 255, 241, 0.56);
    height: 2px;
  }

  .dice-signal-map {
    align-items: center;
    display: grid;
    grid-template-columns: 1fr 34px 1fr 34px 1fr 34px 1fr 34px 1fr;
  }

  .dice-signal-node {
    border: 1px solid rgba(255, 255, 255, 0.2);
    min-height: 92px;
    padding: 18px;
  }

  .dice-signal-node.active {
    background: rgba(31, 63, 189, 0.42);
    border-color: rgba(118, 255, 241, 0.6);
  }

  .dice-signal-node span {
    color: #76fff1;
    display: block;
    font-size: 12px;
    font-weight: 900;
  }

  .dice-signal-node strong {
    display: block;
    font-size: 16px;
    line-height: 1.25;
    margin-top: 18px;
  }

  .dice-signal-axis {
    background: rgba(118, 255, 241, 0.5);
    height: 2px;
  }

  .dice-system-ribbon {
    border-bottom: 1px solid rgba(255, 255, 255, 0.16);
    border-top: 1px solid rgba(255, 255, 255, 0.16);
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-top: 26px;
  }

  .dice-system-ribbon span {
    border-left: 1px solid rgba(255, 255, 255, 0.14);
    color: #dbeafe;
    font-size: 13px;
    font-weight: 850;
    min-height: 54px;
    padding: 18px 14px;
  }

  .dice-system-ribbon span:first-child {
    border-left: 0;
  }

  .dice-signal-stats {
    display: grid;
    gap: 1px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-top: 28px;
  }

  .dice-signal-stat {
    background: rgba(255, 255, 255, 0.08);
    min-height: 140px;
    padding: 20px;
  }

  .dice-signal-stat strong {
    color: #fff;
    display: block;
    font-size: 22px;
    line-height: 1.1;
  }

  .dice-signal-stat span {
    color: #76fff1;
    display: block;
    font-size: 13px;
    font-weight: 900;
    margin-top: 12px;
  }

  .dice-signal-stat p {
    color: #cbd5e1;
    font-size: 12px;
    line-height: 1.5;
    margin: 8px 0 0;
  }

  .dice-section-heading {
    margin: 0 auto 42px;
    max-width: 680px;
    text-align: center;
  }

  .dice-section-heading h2,
  .dice-cta h2 {
    color: var(--ink);
    font-size: 40px;
    font-weight: 900;
    letter-spacing: 0;
    line-height: 1.18;
    margin: 0;
  }

  .dice-section-heading > p:last-child,
  .dice-cta p {
    color: var(--muted);
    font-size: 17px;
    line-height: 1.7;
    margin: 16px 0 0;
  }

  .dice-module {
    background: var(--bg);
  }

  .dice-module-header {
    align-items: center;
    background:
      linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px),
      linear-gradient(0deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px),
      linear-gradient(135deg, #0a1b3d 0%, #112b64 100%);
    background-size: 28px 28px, 28px 28px, auto;
    border-radius: 8px;
    box-shadow: 0 26px 60px rgba(2, 8, 23, 0.2);
    color: #fff;
    display: grid;
    gap: 32px;
    grid-template-columns: 0.9fr 1.1fr;
    overflow: hidden;
    padding: 40px;
  }

  .dice-module-header-copy h3 {
    font-size: 30px;
    font-weight: 900;
    margin: 0;
  }

  .dice-module-header-copy p {
    color: #cfe0fb;
    font-size: 16px;
    font-weight: 650;
    line-height: 1.6;
    margin: 10px 0 0;
  }

  .dice-module-header-media {
    align-items: center;
    display: flex;
    justify-content: center;
  }

  .dice-module-header-image {
    border-radius: 8px;
    box-shadow: 0 20px 50px rgba(2, 8, 23, 0.35);
    display: block;
    max-width: 100%;
    width: 100%;
  }

  .dice-module-body {
    background: #fff;
    border-radius: 8px;
    box-shadow: var(--shadow);
    margin-top: 26px;
    padding: 44px;
  }

  .dice-module-intro {
    margin-bottom: 34px;
  }

  .dice-module-intro h2 {
    font-size: 30px;
    font-weight: 900;
    line-height: 1.25;
    margin: 0;
  }

  .dice-module-intro p {
    color: var(--muted);
    font-size: 16px;
    line-height: 1.7;
    margin: 12px 0 0;
  }

  .dice-module-flow {
    align-items: stretch;
    display: grid;
    gap: 0;
    grid-template-columns: 1fr 28px 1fr 28px 1fr 28px 1fr;
    margin-bottom: 40px;
  }

  .dice-module-flow-step {
    background: var(--surface-soft);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 18px;
  }

  .dice-module-flow-badge {
    background: var(--primary);
    border-radius: 999px;
    color: #fff;
    display: inline-flex;
    font-size: 13px;
    font-weight: 900;
    padding: 6px 14px;
  }

  .dice-module-flow-step p {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.55;
    margin: 14px 0 16px;
    min-height: 58px;
  }

  .dice-module-flow-step .dice-media-slot {
    min-height: 140px;
  }

  .dice-module-flow-image {
    aspect-ratio: 16 / 10;
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 8px;
    display: block;
    object-fit: cover;
    object-position: top;
    width: 100%;
  }

  .dice-module-flow-arrow {
    align-items: center;
    color: var(--line-strong);
    display: flex;
    font-size: 18px;
    font-weight: 900;
    justify-content: center;
  }

  .dice-module-features {
    display: grid;
    gap: 0;
    grid-template-columns: repeat(2, 1fr);
  }

  .dice-module-feature {
    border-top: 1px solid var(--line);
    padding: 24px 0;
  }

  .dice-module-feature:nth-child(odd) {
    border-right: 1px solid var(--line);
    padding-right: 32px;
  }

  .dice-module-feature:nth-child(even) {
    padding-left: 32px;
  }

  .dice-module-feature:nth-child(-n + 2) {
    border-top: 0;
  }

  .dice-card-number {
    align-items: center;
    background: transparent;
    border-radius: 0;
    color: var(--primary);
    display: inline-flex;
    font-size: 14px;
    font-weight: 900;
    height: 26px;
    justify-content: flex-start;
    width: auto;
  }

  .dice-module-feature h3 {
    font-size: 18px;
    line-height: 1.32;
    margin: 12px 0 12px;
  }

  .dice-module-feature ul {
    display: grid;
    gap: 8px;
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .dice-module-feature li {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.6;
    padding-left: 14px;
    position: relative;
  }

  .dice-module-feature li::before {
    background: var(--cyan);
    border-radius: 50%;
    content: "";
    height: 6px;
    left: 0;
    position: absolute;
    top: 8px;
    width: 6px;
  }


  .dice-mini-chart {
    display: block;
    height: 118px;
    width: 100%;
  }

  .dice-mini-chart path {
    fill: none;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .dice-mini-chart .grid {
    stroke: #e5eaf2;
    stroke-width: 1;
  }

  .dice-mini-chart .accent {
    stroke: #9956ff;
    stroke-width: 4;
  }

  .dice-mini-chart .success {
    stroke: #00a879;
    stroke-width: 4;
  }

  .dice-media-slot {
    align-items: center;
    aspect-ratio: 16 / 10;
    background:
      linear-gradient(90deg, rgba(31, 63, 189, 0.1) 1px, transparent 1px),
      linear-gradient(0deg, rgba(31, 63, 189, 0.1) 1px, transparent 1px),
      linear-gradient(135deg, #f8fbff 0%, #eef5fb 100%);
    background-size: 28px 28px;
    border: 1px solid #c9d6e7;
    border-radius: 8px;
    display: flex;
    justify-content: center;
    max-width: 100%;
    min-height: 260px;
    overflow: hidden;
    position: relative;
    width: 100%;
  }

  .dice-media-slot::before {
    background:
      linear-gradient(135deg, transparent 0 46%, rgba(31, 63, 189, 0.1) 46% 47%, transparent 47%),
      linear-gradient(45deg, transparent 0 58%, rgba(0, 200, 184, 0.12) 58% 59%, transparent 59%);
    content: "";
    inset: 0;
    position: absolute;
  }

  .dice-media-slot.compact {
    aspect-ratio: 4 / 5;
    min-height: 260px;
    width: 180px;
  }

  .dice-media-slot span {
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 999px;
    color: var(--primary);
    font-size: 12px;
    font-weight: 900;
    padding: 7px 12px;
    position: relative;
    z-index: 2;
  }

  .dice-media-slot i {
    border: 1px solid rgba(31, 63, 189, 0.26);
    height: 44%;
    position: absolute;
    transform: translate(-10%, -4%);
    width: 54%;
  }

  .dice-media-slot::after {
    background: rgba(31, 63, 189, 0.08);
    bottom: 12%;
    content: "";
    height: 34%;
    position: absolute;
    right: 12%;
    width: 38%;
  }

  .dice-media-slot.tone-1 {
    background-color: #f4fbf9;
  }

  .dice-media-slot.tone-2 {
    background-color: #fffaf0;
  }

  .dice-cases {
    background: #fff;
    overflow: hidden;
  }

  .dice-case-shell {
    position: relative;
  }

  .dice-case-rail {
    display: flex;
    gap: 24px;
    overflow-x: auto;
    padding: 4px 0 18px;
    scroll-snap-type: x mandatory;
    scrollbar-width: none;
  }

  .dice-case-rail::-webkit-scrollbar {
    display: none;
  }

  .dice-case-card {
    background: #fff;
    border: 0;
    border-radius: 8px;
    box-shadow: var(--shadow);
    display: flex;
    flex: 0 0 100%;
    flex-direction: column;
    gap: 28px;
    min-height: 0;
    padding: 34px;
    position: relative;
    scroll-snap-align: center;
  }

  .dice-case-card::before {
    background: linear-gradient(180deg, var(--primary), var(--cyan));
    bottom: 34px;
    content: "";
    left: 34px;
    position: absolute;
    top: 34px;
    width: 3px;
  }

  .dice-case-card .dice-media-slot {
    min-height: 240px;
  }

  .dice-case-image {
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 8px;
    display: block;
    height: auto;
    margin: 0 auto;
    max-height: 320px;
    max-width: 100%;
    object-fit: contain;
    padding: 18px;
  }

  .dice-case-copy {
    padding-left: 20px;
  }

  .dice-case-copy > span {
    color: var(--primary);
    display: block;
    font-size: 13px;
    font-weight: 900;
    margin-bottom: 16px;
    text-transform: uppercase;
  }

  .dice-case-copy h3 {
    font-size: 34px;
    line-height: 1.2;
    margin: 0;
  }

  .dice-case-copy p {
    color: var(--muted);
    font-size: 17px;
    line-height: 1.7;
    margin: 18px 0 0;
  }

  .dice-case-defect {
    font-weight: 650;
  }

  .dice-case-split {
    border-top: 1px solid var(--line);
    display: grid;
    gap: 20px;
    grid-template-columns: repeat(2, 1fr);
    margin-top: 22px;
    padding-top: 22px;
  }

  .dice-case-split strong {
    color: var(--primary);
    display: block;
    font-size: 13px;
    font-weight: 900;
    margin-bottom: 8px;
    text-transform: uppercase;
  }

  .dice-case-split > div > span {
    color: var(--ink);
    display: block;
    font-size: 14px;
    font-weight: 650;
    line-height: 1.55;
  }

  .dice-case-split ul {
    display: grid;
    gap: 6px;
    list-style: none;
    margin: 10px 0 0;
    padding: 0;
  }

  .dice-case-split li {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.55;
    padding-left: 12px;
    position: relative;
  }

  .dice-case-split li::before {
    background: var(--cyan);
    border-radius: 50%;
    content: "";
    height: 5px;
    left: 0;
    position: absolute;
    top: 7px;
    width: 5px;
  }

  .dice-case-controls {
    align-items: center;
    display: flex;
    gap: 16px;
    justify-content: center;
    margin-top: 18px;
  }

  .dice-case-controls > button {
    align-items: center;
    background: #fff;
    border: 1px solid var(--line-strong);
    border-radius: 50%;
    color: var(--primary);
    cursor: pointer;
    display: inline-flex;
    font-size: 18px;
    font-weight: 900;
    height: 40px;
    justify-content: center;
    width: 40px;
  }

  .dice-case-dots {
    display: flex;
    gap: 8px;
  }

  .dice-case-dots button {
    background: #c5cfdd;
    border: 0;
    border-radius: 999px;
    cursor: pointer;
    height: 8px;
    padding: 0;
    transition: width 180ms ease, background 180ms ease;
    width: 8px;
  }

  .dice-case-dots button.active {
    background: var(--primary);
    width: 30px;
  }

  .dice-cta {
    background: #fff;
    padding: 90px 0;
  }

  .dice-cta-inner {
    align-items: center;
    background:
      linear-gradient(90deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px),
      linear-gradient(0deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px),
      #112b64;
    background-size: 28px 28px;
    border-radius: 8px;
    color: #fff;
    display: grid;
    gap: 18px;
    justify-items: center;
    padding: 62px 34px;
    text-align: center;
  }

  .dice-cta h2 {
    color: #fff;
    max-width: 680px;
  }

  .dice-cta p {
    color: #d7e4f8;
    max-width: 620px;
  }

  .dice-cta .dice-primary-link {
    background: #fff;
    color: var(--primary);
  }

  .dice-cta .dice-secondary-link {
    color: #fff;
  }

  .dice-footer {
    background: #fff;
    border-top: 1px solid var(--line);
    color: var(--muted);
    font-size: 14px;
    padding: 28px 0;
  }

  .dice-footer .dice-section-inner {
    align-items: center;
    display: flex;
    justify-content: space-between;
  }

  .dice-footer a {
    color: var(--primary);
    font-weight: 900;
  }

  .dice-reveal {
    opacity: 0;
    transform: translateY(22px);
    transition:
      opacity 560ms ease,
      transform 560ms ease;
  }

  .dice-reveal.is-visible {
    opacity: 1;
    transform: translateY(0);
  }

  .delay-1 {
    transition-delay: 110ms;
  }

  .delay-2 {
    transition-delay: 180ms;
  }

  @media (prefers-reduced-motion: reduce) {
    html {
      scroll-behavior: auto;
    }

    .dice-reveal,
    .dice-primary-link,
    .dice-secondary-link,
    .dice-start-button {
      transition: none;
    }
  }

  @media (max-width: 1120px) {
    .dice-section-inner {
      width: calc(100% - 56px);
    }

    .dice-hero-grid,
    .dice-signal-grid,
    .dice-module-header {
      grid-template-columns: 1fr;
    }

    .dice-hero h1 {
      font-size: 54px;
    }

    .dice-module-flow {
      grid-template-columns: repeat(2, 1fr);
    }

    .dice-module-flow-arrow {
      display: none;
    }

    .dice-signal-stats {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 820px) {
    .dice-header {
      gap: 14px;
      height: auto;
      padding: 12px 20px;
    }

    .dice-nav {
      display: none;
    }

    .dice-header-actions {
      gap: 8px;
    }

    .dice-start-button {
      display: none;
    }

    .dice-section-inner {
      width: calc(100% - 32px);
    }

    .dice-section {
      padding: 72px 0;
    }

    .dice-hero {
      padding: 66px 0 56px;
    }

    .dice-hero h1 {
      font-size: 42px;
    }

    .dice-hero h1 span {
      font-size: 24px;
    }

    .dice-hero-lead {
      font-size: 17px;
    }

    .dice-console-body {
      grid-template-columns: 1fr;
    }

    .dice-console-sidebar {
      display: none;
    }

    .dice-console-metrics {
      border-top: 1px solid var(--line);
    }

    .dice-proof {
      grid-template-columns: repeat(2, 1fr);
    }

    .dice-section-heading h2,
    .dice-signal-copy h2,
    .dice-cta h2 {
      font-size: 32px;
    }

    .dice-module-flow,
    .dice-module-features,
    .dice-case-split,
    .dice-signal-map {
      grid-template-columns: 1fr;
    }

    .dice-module-feature:nth-child(odd) {
      border-right: 0;
      padding-right: 0;
    }

    .dice-module-feature:nth-child(even) {
      padding-left: 0;
    }

    .dice-module-feature:nth-child(-n + 2) {
      border-top: 1px solid var(--line);
    }

    .dice-module-feature:first-child {
      border-top: 0;
    }

    .dice-module-header,
    .dice-module-body {
      padding: 24px;
    }

    .dice-flow-compare {
      grid-template-columns: 1fr;
    }

    .dice-flow-compare > div + div {
      border-left: 0;
      border-top: 1px solid var(--line);
    }

    .dice-flow-lane-nodes,
    .dice-flow-lane.old .dice-flow-lane-nodes,
    .dice-flow-lane.new .dice-flow-lane-nodes {
      grid-template-columns: 1fr;
    }

    .dice-flow-axis {
      height: 28px;
      justify-self: center;
      width: 2px;
    }

    .dice-signal-section {
      padding-bottom: 72px;
    }

    .dice-signal-copy,
    .dice-signal-board {
      padding: 24px;
    }

    .dice-signal-axis {
      height: 28px;
      justify-self: center;
      width: 2px;
    }

    .dice-system-ribbon {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .dice-system-ribbon span:nth-child(2n + 1) {
      border-left: 0;
    }

    .dice-system-ribbon span:nth-child(n + 3) {
      border-top: 1px solid rgba(255, 255, 255, 0.14);
    }

    .dice-hero-console {
      transform: none;
    }

    .dice-module-intro h2,
    .dice-case-copy h3 {
      font-size: 28px;
    }

    .dice-case-card {
      min-height: 0;
      padding: 18px;
    }

    .dice-case-card .dice-media-slot {
      min-height: 260px;
    }

  }

  @media (max-width: 520px) {
    .dice-brand {
      font-size: 16px;
    }

    .dice-hero h1 {
      font-size: 34px;
    }

    .dice-hero h1 span {
      font-size: 20px;
    }

    .dice-hero-actions {
      align-items: stretch;
      flex-direction: column;
    }

    .dice-primary-link,
    .dice-secondary-link {
      width: 100%;
    }

    .dice-proof {
      grid-template-columns: 1fr;
    }

    .dice-industry-wall,
    .dice-signal-stats,
    .dice-system-ribbon {
      grid-template-columns: 1fr;
    }

    .dice-industry-wall span,
    .dice-industry-wall span:nth-child(2n + 1),
    .dice-system-ribbon span,
    .dice-system-ribbon span:nth-child(2n + 1) {
      border-left: 0;
    }

    .dice-industry-wall span:nth-child(n + 2),
    .dice-system-ribbon span:nth-child(n + 2) {
      border-top: 1px solid var(--line);
    }

    .dice-system-ribbon span:nth-child(n + 2) {
      border-top-color: rgba(255, 255, 255, 0.14);
    }

    .dice-module-header,
    .dice-module-body {
      padding: 18px;
    }

    .dice-media-slot.compact {
      width: 100%;
    }

    .dice-footer .dice-section-inner {
      align-items: flex-start;
      flex-direction: column;
      gap: 10px;
    }
  }
`;
