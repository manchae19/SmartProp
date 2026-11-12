// Market Insights data for 6 core districts of Da Nang City
// Extracted from Da Nang Statistical Yearbook, Open Data Portal & Market Reports (Batdongsan, CBRE, VARS)

export const DISTRICT_PROFILES = {
  'Sơn Trà': {
    id: 'son-tra',
    name: 'Quận Sơn Trà',
    shortName: 'Sơn Trà',
    slug: 'son-tra',
    icon: '🏖️',
    image: '/media/projects/the-filmore.jpg',
    viewsCount: '37.637',
    activeListingsCount: '1.674',
    tagline: 'Thủ phủ du lịch biển, bất động sản nghỉ dưỡng & giải trí quốc tế',
    overview: 'Quận Sơn Trà sở hữu vị trí chiến lược ba mặt giáp sông Hàn và biển Đông, ôm trọn bán đảo Sơn Trà và bãi biển Mỹ Khê - một trong những bãi biển đẹp nhất hành tinh. Đây là tâm điểm phát triển kinh tế du lịch, dịch vụ lưu trú cao cấp và bất động sản ven biển có giá trị thương mại hàng đầu Đà Nẵng.',
    lat: 16.0825,
    lon: 108.2464,
    zoom: 13,
    macro: {
      areaKm2: '60.8 km²',
      population: '162.000',
      density: '2.664 người/km²',
      avgPricePerM2: '147,1 triệu/m²',
      priceGrowthYoY: '+9.4%',
      liquidityRating: 'Rất cao (94/100)'
    },
    aiInsights: {
      title: 'Đánh giá tiềm năng đầu tư & Thanh khoản Quận Sơn Trà',
      growthPotential: 'Quỹ đất ven biển ngày càng khan hiếm trong khi nhu cầu khai thác du lịch, khách sạn và căn hộ dịch vụ luôn đạt công suất cao (75 - 85% vào mùa cao điểm). Trục đường Võ Nguyên Giáp, Hoàng Sa và các tuyến nối biển như Nguyễn Đức An, Chu Huy Mân giữ biên độ tăng giá ổn định 10 - 15%/năm.',
      liquidity: 'Thanh khoản phân khúc đất nền diện tích 80 - 150m² đạt mức cao nhất toàn thành phố. Giao dịch diễn ra sôi động từ các nhà đầu tư Hà Nội, TP.HCM tìm kiếm tài sản tích lũy dòng tiền.',
      recommendation: 'Phù hợp đầu tư trung và dài hạn từ 2 - 5 năm kết hợp mô hình kinh doanh lưu trú, căn hộ biển cao cấp hoặc giữ tài sản chống trượt giá.'
    },
    infrastructure: [{
      name: 'Nâng cấp vệt cảnh quan biển Võ Nguyên Giáp & Bán đảo Sơn Trà',
      status: 'Đang triển khai',
      badge: 'bg-emerald-50 text-emerald-700'
    }, {
      name: 'Cụm cầu vượt sông Hàn kết nối trực tiếp quận Hải Châu',
      status: 'Hoàn thành',
      badge: 'bg-blue-50 text-blue-700'
    }, {
      name: 'Quy hoạch khu phố đêm du lịch An Thượng & Chợ đêm Sơn Trà',
      status: 'Đã vận hành',
      badge: 'bg-purple-50 text-purple-700'
    }, {
      name: 'Tuyến du lịch ven biển kết nối Hội An',
      status: 'Trục huyết mạch',
      badge: 'bg-amber-50 text-amber-700'
    }],
    priceHistory: {
      labels: ['Q1/24', 'Q2/24', 'Q3/24', 'Q4/24', 'Q1/25', 'Q2/25', 'Q3/25', 'Q4/25', 'Q1/26', 'Q2/26', 'Q3/26', 'Q4/26'],
      land: [118, 122, 125, 129, 133, 136, 140, 143, 145, 147, 152, 156],
      house: [135, 138, 142, 145, 150, 153, 158, 162, 165, 168, 172, 176],
      apartment: [48, 50, 52, 53, 55, 57, 59, 62, 64, 66, 68, 71]
    }
  },
  'Hải Châu': {
    id: 'hai-chau',
    name: 'Quận Hải Châu',
    shortName: 'Hải Châu',
    slug: 'hai-chau',
    icon: '🏛️',
    image: '/media/projects/sun-cosmo.jpg',
    viewsCount: '34.089',
    activeListingsCount: '1.084',
    tagline: 'Trung tâm hành chính, tài chính - thương mại sầm uất bậc nhất',
    overview: 'Hải Châu là quận trung tâm lịch sử và kinh tế của Đà Nẵng, nơi quy tụ trụ sở các cơ quan ban ngành, ngân hàng, trường đại học lớn và các tuyến phố tài chính Bạch Đằng, Trần Phú, Hùng Vương. BĐS tại đây có tính khan hiếm cao, giá trị khai thác kinh doanh thương mại luôn duy trì vị thế dẫn đầu.',
    lat: 16.0544,
    lon: 108.2195,
    zoom: 14,
    macro: {
      areaKm2: '8.4 km²',
      population: '205.000',
      density: '24.405 người/km²',
      avgPricePerM2: '103,4 triệu/m²',
      priceGrowthYoY: '+6.8%',
      liquidityRating: 'Rất ổn định (92/100)'
    },
    aiInsights: {
      title: 'Đánh giá tiềm năng đầu tư & Thanh khoản Quận Hải Châu',
      growthPotential: 'Quỹ đất trống gần như cạn kiệt, nguồn cung mới chủ yếu là các dự án căn hộ hạng sang ven sông Hàn. Giá trị tài sản gia tăng bền vững nhờ tỷ suất cho thuê kinh doanh mặt bằng và dòng tiền văn phòng ổn định.',
      liquidity: 'Thanh khoản ổn định, tỷ lệ trả giá thấp do các chủ sở hữu lâu năm ít có áp lực tài chính buộc phải bán gấp.',
      recommendation: 'Ưu tiên dòng vốn an toàn muốn bảo toàn vốn, khai thác dòng tiền cho thuê văn phòng, cửa hàng thời trang hoặc nhà ở trung tâm.'
    },
    infrastructure: [{
      name: 'Tuyến phố đi bộ Bạch Đằng & Công viên APEC mở rộng',
      status: 'Đã hoàn thành',
      badge: 'bg-emerald-50 text-emerald-700'
    }, {
      name: 'Cải tạo chỉnh trang đô thị các tuyến phố chuyên doanh',
      status: 'Đang triển khai',
      badge: 'bg-blue-50 text-blue-700'
    }, {
      name: 'Khu công viên phần mềm số 1 & mở rộng Trung tâm Tài chính',
      status: 'Trọng điểm 2026',
      badge: 'bg-purple-50 text-purple-700'
    }],
    priceHistory: {
      labels: ['Q1/24', 'Q2/24', 'Q3/24', 'Q4/24', 'Q1/25', 'Q2/25', 'Q3/25', 'Q4/25', 'Q1/26', 'Q2/26', 'Q3/26', 'Q4/26'],
      land: [88, 90, 92, 94, 96, 98, 100, 102, 103, 104, 106, 108],
      house: [110, 112, 115, 118, 120, 123, 125, 128, 130, 133, 135, 138],
      apartment: [52, 54, 56, 58, 60, 63, 65, 68, 70, 72, 75, 78]
    }
  },
  'Liên Chiểu': {
    id: 'lien-chieu',
    name: 'Quận Liên Chiểu',
    shortName: 'Liên Chiểu',
    slug: 'lien-chieu',
    icon: '🚢',
    image: '/media/projects/sun-symphony.jpg',
    viewsCount: '31.355',
    activeListingsCount: '823',
    tagline: 'Đô thị công nghiệp công nghệ cao, logistics & Cảng nước sâu',
    overview: 'Liên Chiểu là cửa ngõ phía Bắc của Đà Nẵng, trung tâm công nghiệp lớn với KCN Hòa Khánh, Khu Công nghệ cao và siêu dự án Cảng Liên Chiểu. Với quỹ đất rộng lớn, trục đại lộ Nguyễn Sinh Sắc và vệt biển vịnh Đà Nẵng, Liên Chiểu là điểm đến hấp dẫn cho giới đầu tư săn đón tiềm năng bứt phá hạ tầng.',
    lat: 16.0886,
    lon: 108.1528,
    zoom: 13,
    macro: {
      areaKm2: '82.5 km²',
      population: '170.000',
      density: '2.060 người/km²',
      avgPricePerM2: '95,7 triệu/m²',
      priceGrowthYoY: '+14.2%',
      liquidityRating: 'Tăng trưởng mạnh (89/100)'
    },
    aiInsights: {
      title: 'Đánh giá tiềm năng đầu tư & Thanh khoản Quận Liên Chiểu',
      growthPotential: 'Hưởng lợi trực tiếp từ tiến độ giải ngân dự án Cảng Liên Chiểu và các khu công nghệ bán dẫn, phần mềm FPT. Đơn giá đất nền đường lớn (Nguyễn Sinh Sắc, Nguyễn Tất Thành) còn thấp hơn nhiều so với Sơn Trà/Hải Châu nên biên độ tăng giá còn rất rộng.',
      liquidity: 'Lượng giao dịch đất nền phân lô tái định cư và đất dự án quanh trục hành chính tăng mạnh trong 4 quý gần nhất.',
      recommendation: 'Lý tưởng cho nhà đầu tư săn đón làn sóng tăng trưởng theo chu kỳ hoàn thiện hạ tầng cảng biển và khu công nghệ cao.'
    },
    infrastructure: [{
      name: 'Đại dự án Cảng biển nước sâu Liên Chiểu (Giai đoạn 1)',
      status: 'Đang tăng tốc',
      badge: 'bg-emerald-50 text-emerald-700'
    }, {
      name: 'Khu công nghệ cao Đà Nẵng & Trung tâm nghiên cứu Vi mạch',
      status: 'Mở rộng 2026',
      badge: 'bg-purple-50 text-purple-700'
    }, {
      name: 'Tuyến đường ven biển Nguyễn Tất Thành kết nối Nam Ô',
      status: 'Hoàn thành',
      badge: 'bg-blue-50 text-blue-700'
    }],
    priceHistory: {
      labels: ['Q1/24', 'Q2/24', 'Q3/24', 'Q4/24', 'Q1/25', 'Q2/25', 'Q3/25', 'Q4/25', 'Q1/26', 'Q2/26', 'Q3/26', 'Q4/26'],
      land: [62, 65, 68, 72, 76, 80, 85, 89, 92, 96, 102, 112],
      house: [70, 73, 76, 80, 84, 88, 93, 97, 100, 105, 110, 118],
      apartment: [28, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47, 50]
    }
  },
  'Ngũ Hành Sơn': {
    id: 'ngu-hanh-son',
    name: 'Quận Ngũ Hành Sơn',
    shortName: 'Ngũ Hành Sơn',
    slug: 'ngu-hanh-son',
    icon: '🌊',
    image: '/media/projects/sun-ponte.jpg',
    viewsCount: '33.348',
    activeListingsCount: '918',
    tagline: 'Thủ phủ resort nghỉ dưỡng 5 sao, làng đại học & BĐS sinh thái',
    overview: 'Quận Ngũ Hành Sơn sở hữu vệt bờ biển dài thơ mộng nối liền Đà Nẵng với Hội An, danh thắng Non Nước và Làng đại học Đà Nẵng. Đây là địa bàn tập trung mật độ resort 5 sao lớn nhất Việt Nam (Hyatt, Furama, Sheraton, Vinpearl), thu hút giới siêu giàu và chuyên gia quốc tế.',
    lat: 16.0125,
    lon: 108.2564,
    zoom: 13,
    macro: {
      areaKm2: '37.4 km²',
      population: '92.000',
      density: '2.460 người/km²',
      avgPricePerM2: '91,7 triệu/m²',
      priceGrowthYoY: '+11.5%',
      liquidityRating: 'Tốt (87/100)'
    },
    aiInsights: {
      title: 'Đánh giá tiềm năng đầu tư & Thanh khoản Quận Ngũ Hành Sơn',
      growthPotential: 'Sự phát triển của Làng Đại học Đà Nẵng và Khu công nghệ FPT City tạo lực cầu nhà ở và phòng trọ, căn hộ cho thuê cực lớn. Các phân khu ven sông Cổ Cò đón đầu quy hoạch khơi thông sông kết nối Hội An.',
      liquidity: 'Phân khúc đất nền đô thị sinh thái Hòa Quý, Hòa Hải và biệt thự ven sông có giao dịch chuyển nhượng ổn định.',
      recommendation: 'Thích hợp cho cả mục đích an cư sinh thái yên bình lẫn đầu tư trung hạn theo tiến độ thông luồng du lịch sông Cổ Cò.'
    },
    infrastructure: [{
      name: 'Dự án nạo vét khơi thông sông Cổ Cò kết nối Đà Nẵng - Hội An',
      status: 'Giai đoạn cuối',
      badge: 'bg-emerald-50 text-emerald-700'
    }, {
      name: 'Khu đô thị công nghệ cao FPT City & Đại học FPT',
      status: 'Đang mở rộng',
      badge: 'bg-purple-50 text-purple-700'
    }, {
      name: 'Làng Đại học Đà Nẵng tại Hòa Quý',
      status: 'Tập trung nguồn vốn',
      badge: 'bg-blue-50 text-blue-700'
    }],
    priceHistory: {
      labels: ['Q1/24', 'Q2/24', 'Q3/24', 'Q4/24', 'Q1/25', 'Q2/25', 'Q3/25', 'Q4/25', 'Q1/26', 'Q2/26', 'Q3/26', 'Q4/26'],
      land: [70, 72, 75, 78, 81, 84, 87, 90, 92, 94, 98, 102],
      house: [85, 88, 91, 94, 98, 101, 105, 109, 112, 116, 120, 125],
      apartment: [35, 37, 39, 41, 43, 45, 47, 50, 52, 54, 57, 60]
    }
  },
  'Cẩm Lệ': {
    id: 'cam-le',
    name: 'Quận Cẩm Lệ',
    shortName: 'Cẩm Lệ',
    slug: 'cam-le',
    icon: '🏡',
    image: '/media/projects/sunneva-island.jpg',
    viewsCount: '30.328',
    activeListingsCount: '718',
    tagline: 'Khu đô thị sinh thái ven sông mở rộng, dân cư trẻ năng động',
    overview: 'Cẩm Lệ là quận nội thành kết nối giữa trung tâm Hải Châu với các vùng kinh tế vệ tinh phía Nam Đà Nẵng. Quận sở hữu hệ thống hạ tầng giao thông kết nối đồng bộ, bến xe trung tâm, các khu đô thị sinh thái ven sông Cẩm Lệ như Hòa Xuân, Nam cầu Cẩm Lệ.',
    lat: 16.0225,
    lon: 108.2045,
    zoom: 13,
    macro: {
      areaKm2: '33.7 km²',
      population: '145.000',
      density: '4.302 người/km²',
      avgPricePerM2: '125,0 triệu/m²',
      priceGrowthYoY: '+8.0%',
      liquidityRating: 'Tốt (86/100)'
    },
    aiInsights: {
      title: 'Đánh giá tiềm năng đầu tư & Thanh khoản Quận Cẩm Lệ',
      growthPotential: 'Được mệnh danh là thiên đường nhà ở thực nhờ quy hoạch ô bàn cờ vuông vắn, công viên cây xanh ven sông, hạ tầng điện ngầm hoàn chỉnh. Nhu cầu định cư của các gia đình trẻ từ các tỉnh miền Trung chuyển về làm việc tại Đà Nẵng rất cao.',
      liquidity: 'Thanh khoản phân khúc nhà phố hoàn thiện và đất nền các block ven sông đạt chỉ số hấp thụ rất nhanh.',
      recommendation: 'Lựa chọn số 1 cho người mua ở thực và nhà đầu tư chuộng sự bền vững, ít biến động sốc theo thị trường đầu cơ.'
    },
    infrastructure: [{
      name: 'Khu đô thị sinh thái Hòa Xuân & Nam Hòa Xuân',
      status: 'Hoàn thiện 95%',
      badge: 'bg-emerald-50 text-emerald-700'
    }, {
      name: 'Cụm cầu Hòa Xuân và mở rộng trục Nguyễn Tri Phương',
      status: 'Vận hành tốt',
      badge: 'bg-blue-50 text-blue-700'
    }, {
      name: 'Cụm công nghiệp Cẩm Lệ phục vụ doanh nghiệp vừa và nhỏ',
      status: 'Đang thu hút',
      badge: 'bg-purple-50 text-purple-700'
    }],
    priceHistory: {
      labels: ['Q1/24', 'Q2/24', 'Q3/24', 'Q4/24', 'Q1/25', 'Q2/25', 'Q3/25', 'Q4/25', 'Q1/26', 'Q2/26', 'Q3/26', 'Q4/26'],
      land: [90, 93, 96, 100, 104, 108, 112, 116, 119, 122, 125, 128],
      house: [105, 108, 112, 116, 120, 125, 129, 134, 138, 142, 146, 150],
      apartment: [32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 55]
    }
  },
  'Thanh Khê': {
    id: 'thanh-khe',
    name: 'Quận Thanh Khê',
    shortName: 'Thanh Khê',
    slug: 'thanh-khe',
    icon: '🏬',
    image: '/media/home/hero-poster.jpg',
    viewsCount: '28.940',
    activeListingsCount: '663',
    tagline: 'Đầu mối giao thông đường sắt, cảng cá & thương mại mật độ cao',
    overview: 'Thanh Khê là quận có mật độ dân số cao nhất thành phố, trải dài dọc theo vịnh Đà Nẵng và trục đường Điện Biên Phủ, Nguyễn Tất Thành. Quận sở hữu Ga đường sắt Đà Nẵng, cửa ngõ giao thương hàng hóa và mạng lưới buôn bán tiểu thương sầm uất.',
    lat: 16.0622,
    lon: 108.1885,
    zoom: 14,
    macro: {
      areaKm2: '9.5 km²',
      population: '190.000',
      density: '20.000 người/km²',
      avgPricePerM2: '89,8 triệu/m²',
      priceGrowthYoY: '+5.5%',
      liquidityRating: 'Ổn định (85/100)'
    },
    aiInsights: {
      title: 'Đánh giá tiềm năng đầu tư & Thanh khoản Quận Thanh Khê',
      growthPotential: 'Quy hoạch di dời Ga Đà Nẵng trong tương lai để phát triển tổ hợp đô thị thương mại hiện đại sẽ tạo cú hích lớn tái thiết diện mạo khu vực. Trục đường Điện Biên Phủ giữ vững vị thế tuyến phố tài chính - bán lẻ sầm uất.',
      liquidity: 'Nhà trong ngõ kiệt có mức giá vừa túi tiền cho người lao động, thời gian thanh khoản trung bình 30 - 45 ngày.',
      recommendation: 'Phù hợp mua để ở, kinh doanh buôn bán hộ gia đình hoặc giữ tiền qua tài sản nhà liền thổ.'
    },
    infrastructure: [{
      name: 'Kế hoạch di dời Ga đường sắt Đà Nẵng & Tái thiết đô thị',
      status: 'Quy hoạch tầm nhìn',
      badge: 'bg-amber-50 text-amber-700'
    }, {
      name: 'Chỉnh trang bãi biển vịnh Thanh Khê & tuyến Nguyễn Tất Thành',
      status: 'Đang triển khai',
      badge: 'bg-emerald-50 text-emerald-700'
    }, {
      name: 'Nút giao thông khác mức Ngã ba Huế kết nối liên vùng',
      status: 'Hoàn thành',
      badge: 'bg-blue-50 text-blue-700'
    }],
    priceHistory: {
      labels: ['Q1/24', 'Q2/24', 'Q3/24', 'Q4/24', 'Q1/25', 'Q2/25', 'Q3/25', 'Q4/25', 'Q1/26', 'Q2/26', 'Q3/26', 'Q4/26'],
      land: [72, 74, 76, 78, 80, 82, 84, 86, 88, 90, 92, 94],
      house: [85, 87, 90, 92, 95, 98, 101, 104, 107, 110, 113, 116],
      apartment: [30, 31, 33, 34, 36, 38, 40, 42, 44, 46, 48, 50]
    }
  }
};
export const DISTRICT_LIST = Object.keys(DISTRICT_PROFILES);
export function getDistrictProfile(districtName) {
  if (!districtName) return DISTRICT_PROFILES['Sơn Trà'];
  const norm = districtName.trim();
  for (const [key, value] of Object.entries(DISTRICT_PROFILES)) {
    if (key.toLowerCase() === norm.toLowerCase() || value.shortName.toLowerCase() === norm.toLowerCase() || value.slug === norm.toLowerCase() || norm.toLowerCase().includes(value.shortName.toLowerCase())) {
      return value;
    }
  }
  return DISTRICT_PROFILES['Sơn Trà'];
}
