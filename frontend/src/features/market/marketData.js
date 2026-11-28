// Administrative & geographic reference profiles for all 7 districts/counties of Da Nang City.
// Contains ONLY static administrative/planning reference context — zero hardcoded market prices,
// zero YoY growth forecasts, zero liquidity scores, zero synthetic quarterly price series,
// and zero unverified location photographs.

export const DISTRICT_PROFILES = Object.freeze({
  'Sơn Trà': Object.freeze({
    id: 'son-tra',
    name: 'Quận Sơn Trà',
    shortName: 'Sơn Trà',
    slug: 'son-tra',
    administrativeType: 'Quận ven biển',
    motif: 'coastal',
    tagline: 'Bán đảo sinh thái, hành lang biển Đông và dịch vụ du lịch ven sông Hàn',
    overview:
      'Quận Sơn Trà nằm ở phía Đông Bắc trung tâm Đà Nẵng, ba mặt giáp sông Hàn và biển Đông, bao gồm bán đảo Sơn Trà và trục ven biển Võ Nguyên Giáp – Hoàng Sa. Khu vực kết hợp khu dân cư hiện hữu, thương mại dịch vụ du lịch và không gian bảo tồn cảnh quan.',
    lat: 16.0825,
    lon: 108.2464,
    zoom: 13,
    macro: Object.freeze({
      areaKm2: '60,8 km²',
      population: '162.000',
      density: '2.664 người/km²',
    }),
    regionalNotes: Object.freeze({
      spatialContext:
        'Kết nối trực tiếp trung tâm Hải Châu qua hệ thống cầu Sông Hàn, cầu Rồng, cầu Thuận Phước và cầu Nguyễn Văn Trỗi – Trần Thị Lý; trục Võ Nguyên Giáp – Phạm Văn Đồng kết nối thẳng ra biển.',
      urbanCharacteristics:
        'Mật độ lưu trú du lịch, căn hộ thương mại và nhà phố dịch vụ tập trung dọc các tuyến nối biển; các khu dân cư phía Tây giáp sông Hàn ưu tiên nhu cầu ở thực.',
      surveyChecklist:
        'Khi khảo sát thực địa cần đối chiếu hành lang bảo vệ bờ biển, giới hạn tầng cao quy hoạch phân khu ven biển, lộ giới kiệt/hẻm và hồ sơ pháp lý gốc của từng thửa đất.',
    }),
    infrastructure: Object.freeze([
      Object.freeze({
        name: 'Tuyến cảnh quan ven biển Võ Nguyên Giáp – Hoàng Sa & Bán đảo Sơn Trà',
        status: 'Hạ tầng hiện hữu',
      }),
      Object.freeze({
        name: 'Cụm cầu vượt sông Hàn kết nối trực tiếp quận Hải Châu',
        status: 'Đang vận hành',
      }),
      Object.freeze({
        name: 'Khu phố du lịch An Thượng & dịch vụ kinh tế đêm ven biển',
        status: 'Đang vận hành',
      }),
      Object.freeze({
        name: 'Trục du lịch ven biển liên kết Đà Nẵng – Quảng Nam',
        status: 'Trục kết nối vùng',
      }),
    ]),
  }),

  'Hải Châu': Object.freeze({
    id: 'hai-chau',
    name: 'Quận Hải Châu',
    shortName: 'Hải Châu',
    slug: 'hai-chau',
    administrativeType: 'Quận trung tâm',
    motif: 'urban-core',
    tagline: 'Trung tâm hành chính, thương mại – tài chính và hạ tầng đô thị lõi bờ Tây sông Hàn',
    overview:
      'Quận Hải Châu là địa bàn trung tâm hành chính, y tế, giáo dục và thương mại lâu đời của Đà Nẵng, quy tụ các trục Bạch Đằng, Trần Phú, Nguyễn Văn Linh, 2 Tháng 9 và khu vực quanh Sân bay Quốc tế Đà Nẵng.',
    lat: 16.0544,
    lon: 108.2195,
    zoom: 14,
    macro: Object.freeze({
      areaKm2: '23,3 km²',
      population: '205.000',
      density: '8.798 người/km²',
    }),
    regionalNotes: Object.freeze({
      spatialContext:
        'Nằm dọc bờ Tây sông Hàn và bao quanh Sân bay Quốc tế Đà Nẵng; tiếp giáp trực tiếp Thanh Khê, Cẩm Lệ và kết nối sang Sơn Trà, Ngũ Hành Sơn qua các cầu trung tâm.',
      urbanCharacteristics:
        'Quỹ đất khu dân cư nội đô đã phát triển ổn định lâu năm; xen kẽ nhà phố mặt tiền thương mại, kiệt/hẻm nội thành và các tòa căn hộ/văn phòng dọc sông Hàn.',
      surveyChecklist:
        'Lưu ý kiểm tra tĩnh không sân bay, chỉ giới đường đỏ các tuyến cải tạo chỉnh trang nội đô, chiều rộng thực tế của kiệt/hẻm và tình trạng ngập cục bộ khi mưa lớn.',
    }),
    infrastructure: Object.freeze([
      Object.freeze({
        name: 'Phố đi bộ Bạch Đằng & không gian công cộng ven sông Hàn – Công viên APEC',
        status: 'Đang vận hành',
      }),
      Object.freeze({
        name: 'Cải tạo hạ tầng thoát nước & ngầm hóa các tuyến phố trung tâm',
        status: 'Định hướng chỉnh trang',
      }),
      Object.freeze({
        name: 'Cụm Công viên Phần mềm Đà Nẵng & hạ tầng công nghệ thông tin nội đô',
        status: 'Hạ tầng trọng điểm',
      }),
    ]),
  }),

  'Liên Chiểu': Object.freeze({
    id: 'lien-chieu',
    name: 'Quận Liên Chiểu',
    shortName: 'Liên Chiểu',
    slug: 'lien-chieu',
    administrativeType: 'Quận cửa ngõ Tây Bắc',
    motif: 'port-tech',
    tagline: 'Cửa ngõ giao thông phía Bắc, cảng biển Liên Chiểu, công nghiệp và đại học',
    overview:
      'Quận Liên Chiểu nằm dọc vịnh Đà Nẵng ở phía Tây Bắc thành phố, giữ vai trò đầu mối giao thông liên vùng qua hầm Hải Vân, Quốc lộ 1A, đường Nguyễn Tất Thành và nơi đặt dự án Cảng Liên Chiểu cùng hệ thống khu công nghiệp, trường đại học.',
    lat: 16.0886,
    lon: 108.1528,
    zoom: 13,
    macro: Object.freeze({
      areaKm2: '74,4 km²',
      population: '170.000',
      density: '2.285 người/km²',
    }),
    regionalNotes: Object.freeze({
      spatialContext:
        'Kết nối phía Bắc qua hầm đường bộ Hải Vân, phía Tây giáp huyện Hòa Vang (Khu Công nghệ cao), phía Đông mở ra vịnh Đà Nẵng theo trục Nguyễn Tất Thành – Nguyễn Sinh Sắc.',
      urbanCharacteristics:
        'Phân bố đa dạng từ các khu đô thị quy hoạch Tây Bắc, khu tái định cư, nhà ở phục vụ giảng viên – sinh viên – chuyên gia đến quỹ đất ven vịnh.',
      surveyChecklist:
        'Cần kiểm tra kỹ ranh giới quy hoạch hành lang đường sắt, đường kết nối cảng Liên Chiểu, cao độ nền thoát nước khu vực Hòa Khánh – Hòa Minh và giấy tờ pháp lý từng lô.',
    }),
    infrastructure: Object.freeze([
      Object.freeze({
        name: 'Dự án đầu tư xây dựng Bến cảng Liên Chiểu & đường ven biển nối cảng',
        status: 'Đang triển khai',
      }),
      Object.freeze({
        name: 'Hành lang kết nối Khu Công nghệ cao Đà Nẵng & các khu công nghiệp Tây Bắc',
        status: 'Trục liên kết vùng',
      }),
      Object.freeze({
        name: 'Tuyến đường ven vịnh Nguyễn Tất Thành – khu vực Nam Ô',
        status: 'Hạ tầng hiện hữu',
      }),
    ]),
  }),

  'Ngũ Hành Sơn': Object.freeze({
    id: 'ngu-hanh-son',
    name: 'Quận Ngũ Hành Sơn',
    shortName: 'Ngũ Hành Sơn',
    slug: 'ngu-hanh-son',
    administrativeType: 'Quận ven biển phía Nam',
    motif: 'eco-coast',
    tagline: 'Hành lang biển phía Đông Nam, danh thắng Ngũ Hành Sơn, công nghệ và đại học',
    overview:
      'Quận Ngũ Hành Sơn nằm ở cửa ngõ Đông Nam Đà Nẵng, trải dọc tuyến biển Trường Sa – Non Nước kết nối Hội An, đồng thời bao gồm khu đô thị công nghệ FPT, khu vực Hòa Quý – sông Cổ Cò và cụm danh thắng quốc gia đặc biệt Ngũ Hành Sơn.',
    lat: 16.0125,
    lon: 108.2564,
    zoom: 13,
    macro: Object.freeze({
      areaKm2: '39,1 km²',
      population: '92.000',
      density: '2.353 người/km²',
    }),
    regionalNotes: Object.freeze({
      spatialContext:
        'Tiếp giáp Sơn Trà ở phía Bắc, Cẩm Lệ và Hòa Vang qua hệ thống sông Hàn – Cẩm Lệ – Vĩnh Điện ở phía Tây, và tỉnh Quảng Nam ở phía Nam theo trục Lê Văn Hiến – Trần Đại Nghĩa – Trường Sa.',
      urbanCharacteristics:
        'Kết hợp dải nghỉ dưỡng ven biển, khu đô thị công nghệ – giáo dục đại học phía Nam và các khu dân cư đô thị hóa tại Mỹ An, Khuê Mỹ, Hòa Hải, Hòa Quý.',
      surveyChecklist:
        'Đối chiếu quy hoạch bảo tồn cảnh quan danh thắng Ngũ Hành Sơn, hành lang thoát lũ ven sông Cổ Cò – Vĩnh Điện và tiến độ hạ tầng thực tế tại các phân khu mới.',
    }),
    infrastructure: Object.freeze([
      Object.freeze({
        name: 'Tuyến ven biển Trường Sa & trục Lê Văn Hiến – Trần Đại Nghĩa kết nối phía Nam',
        status: 'Hạ tầng hiện hữu',
      }),
      Object.freeze({
        name: 'Khu đô thị công nghệ FPT Đà Nẵng & không gian đổi mới sáng tạo',
        status: 'Đang vận hành',
      }),
      Object.freeze({
        name: 'Quy hoạch Khu đô thị Đại học Đà Nẵng tại Hòa Quý',
        status: 'Quy hoạch phân khu',
      }),
    ]),
  }),

  'Cẩm Lệ': Object.freeze({
    id: 'cam-le',
    name: 'Quận Cẩm Lệ',
    shortName: 'Cẩm Lệ',
    slug: 'cam-le',
    administrativeType: 'Quận nội đô mở rộng',
    motif: 'river-eco',
    tagline: 'Đô thị ven sông Cẩm Lệ, đầu mối giao thông phía Tây Nam và khu dân cư quy hoạch đồng bộ',
    overview:
      'Quận Cẩm Lệ giữ vị trí chuyển tiếp chiến lược giữa khu trung tâm Hải Châu – Thanh Khê với huyện Hòa Vang và phía Nam thành phố, nổi bật với hệ thống sông Cẩm Lệ – Đô Tỏa cùng các khu đô thị quy hoạch tại Hòa Xuân, Hòa Thọ và Khuê Trung.',
    lat: 16.0225,
    lon: 108.2045,
    zoom: 13,
    macro: Object.freeze({
      areaKm2: '35,2 km²',
      population: '145.000',
      density: '4.119 người/km²',
    }),
    regionalNotes: Object.freeze({
      spatialContext:
        'Kết nối qua cụm cầu Hòa Xuân, cầu Nguyễn Tri Phương, cầu Cẩm Lệ, cầu vượt Ngã ba Huế và trục Cách Mạng Tháng Tám – Quốc lộ 14B đi Tây Nguyên.',
      urbanCharacteristics:
        'Tỷ trọng lớn là khu dân cư quy hoạch đường bàn cờ, nhà phố ở thực tại Hòa Xuân, Khuê Trung và các trục thương mại nội quận.',
      surveyChecklist:
        'Cần kiểm tra lịch sử ngập lụt theo từng cao trình tuyến đường ven sông (đặc biệt mùa mưa bão miền Trung), hạ tầng thoát nước và giấy chứng nhận quyền sử dụng đất.',
    }),
    infrastructure: Object.freeze([
      Object.freeze({
        name: 'Các khu đô thị ven sông Hòa Xuân & cụm cầu kết nối Hải Châu – Ngũ Hành Sơn',
        status: 'Đang vận hành',
      }),
      Object.freeze({
        name: 'Trục giao thông Cách Mạng Tháng Tám – Trường Chinh – Quốc lộ 14B',
        status: 'Trục huyết mạch',
      }),
      Object.freeze({
        name: 'Cụm công nghiệp Cẩm Lệ & hạ tầng dịch vụ hậu cần nội đô',
        status: 'Đang vận hành',
      }),
    ]),
  }),

  'Thanh Khê': Object.freeze({
    id: 'thanh-khe',
    name: 'Quận Thanh Khê',
    shortName: 'Thanh Khê',
    slug: 'thanh-khe',
    administrativeType: 'Quận trung tâm thương mại',
    motif: 'transit-hub',
    tagline: 'Trục giao thương Điện Biên Phủ – Nguyễn Tất Thành, ga đường sắt và khu dân cư mật độ cao',
    overview:
      'Quận Thanh Khê nằm tiếp giáp trực tiếp quận Hải Châu và vịnh Đà Nẵng, là địa bàn có mật độ dân cư và hoạt động thương mại – dịch vụ tiểu thương sôi động dọc các trục Điện Biên Phủ, Lê Duẩn, Hùng Vương, Hà Huy Tập và Nguyễn Tất Thành.',
    lat: 16.0622,
    lon: 108.1885,
    zoom: 14,
    macro: Object.freeze({
      areaKm2: '9,5 km²',
      population: '190.000',
      density: '20.000 người/km²',
    }),
    regionalNotes: Object.freeze({
      spatialContext:
        'Nằm ngay cửa ngõ vào trung tâm qua nút giao Ngã ba Huế, sở hữu mặt tiền biển vịnh Đà Nẵng phía Bắc và kết nối thẳng tới sân bay, ga Đà Nẵng.',
      urbanCharacteristics:
        'Nhà phố thương mại dọc trục chính đan xen mạng lưới kiệt/hẻm dân cư hiện hữu lâu đời, đáp ứng nhu cầu ở thực gắn với tiện ích trường học, chợ và bệnh viện.',
      surveyChecklist:
        'Kiểm tra quy hoạch hành lang an toàn đường sắt, lộ giới mở rộng kiệt/hẻm, khả năng tiếp cận xe cứu hỏa và hiện trạng thoát nước tại các khu dân cư trũng.',
    }),
    infrastructure: Object.freeze([
      Object.freeze({
        name: 'Nút giao thông khác mức Ngã ba Huế & trục Điện Biên Phủ',
        status: 'Đang vận hành',
      }),
      Object.freeze({
        name: 'Tuyến cảnh quan biển vịnh Thanh Khê – Nguyễn Tất Thành',
        status: 'Hạ tầng hiện hữu',
      }),
      Object.freeze({
        name: 'Định hướng tái thiết không gian đô thị khu vực Ga đường sắt Đà Nẵng',
        status: 'Quy hoạch tầm nhìn',
      }),
    ]),
  }),

  'Hòa Vang': Object.freeze({
    id: 'hoa-vang',
    name: 'Huyện Hòa Vang',
    shortName: 'Hòa Vang',
    slug: 'hoa-vang',
    administrativeType: 'Huyện ngoại thành – sinh thái',
    motif: 'highland-rural',
    tagline: 'Vùng đệm sinh thái phía Tây, Khu Công nghệ cao, logistics liên vùng và đô thị sườn đồi',
    overview:
      'Huyện Hòa Vang bao quanh khu vực nội thành Đà Nẵng về phía Tây, Bắc và Nam, chiếm phần lớn diện tích tự nhiên toàn thành phố với hệ sinh thái rừng – sông suối, Khu Công nghệ cao Đà Nẵng, Khu CNTT tập trung và các tuyến cao tốc liên vùng.',
    lat: 16.0178,
    lon: 108.1186,
    zoom: 11,
    macro: Object.freeze({
      areaKm2: '733,2 km²',
      population: '150.000',
      density: '205 người/km²',
    }),
    regionalNotes: Object.freeze({
      spatialContext:
        'Giao điểm của cao tốc La Sơn – Túy Loan, cao tốc Đà Nẵng – Quảng Ngãi, Quốc lộ 14B, Quốc lộ 1A tránh Nam Hải Vân và đường vành đai phía Tây.',
      urbanCharacteristics:
        'Bao gồm trung tâm hành chính Túy Loan (Hòa Phong), các xã ven đô Hòa Châu, Hòa Tiến, Hòa Phước, Hòa Liên, Hòa Sơn và vùng sinh thái Hòa Bắc, Hòa Phú, Hòa Ninh.',
      surveyChecklist:
        'Bắt buộc đối chiếu mục đích sử dụng đất trên sổ (đất ở nông thôn, đất trồng cây lâu năm, đất rừng), ranh giới quy hoạch thoát lũ sông Yên – Túy Loan và hành lang các dự án giao thông lớn.',
    }),
    infrastructure: Object.freeze([
      Object.freeze({
        name: 'Khu Công nghệ cao Đà Nẵng & Khu Công nghệ thông tin tập trung (Hòa Liên)',
        status: 'Đang vận hành',
      }),
      Object.freeze({
        name: 'Tuyến cao tốc La Sơn – Hòa Liên – Túy Loan & nâng cấp Quốc lộ 14B',
        status: 'Đang triển khai',
      }),
      Object.freeze({
        name: 'Đường Vành đai phía Tây & trục kết nối trung tâm hành chính Hòa Phong',
        status: 'Hạ tầng liên vùng',
      }),
    ]),
  }),
});

export const DISTRICT_LIST = Object.freeze(Object.keys(DISTRICT_PROFILES));
export const DEFAULT_DISTRICT_SLUG = 'son-tra';

function normalizeDistrictToken(value) {
  return String(value ?? '')
    .normalize('NFC')
    .trim()
    .toLocaleLowerCase('vi')
    .replace(/^(?:quận|huyện|thị xã|thành phố)\s+/u, '')
    .replace(/hoà/gu, 'hòa')
    .replace(/\s+/g, ' ');
}

function toAsciiSlug(value) {
  return normalizeDistrictToken(value)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/**
 * Resolves one of the 7 Da Nang administrative units by canonical name, shortName,
 * or URL slug. Returns `null` when `districtName` is empty or does not match any
 * supported Da Nang unit — NEVER falls back to 'Sơn Trà' for unknown slugs.
 */
export function getDistrictProfile(districtName) {
  if (districtName == null) return null;
  const raw = String(districtName).trim();
  if (!raw) return null;

  const norm = normalizeDistrictToken(raw);
  const slug = toAsciiSlug(raw);

  for (const profile of Object.values(DISTRICT_PROFILES)) {
    const profileShort = normalizeDistrictToken(profile.shortName);
    const profileName = normalizeDistrictToken(profile.name);
    if (
      norm === profileShort
      || norm === profileName
      || slug === profile.slug
      || raw.toLowerCase() === profile.slug
    ) {
      return profile;
    }
  }
  return null;
}
