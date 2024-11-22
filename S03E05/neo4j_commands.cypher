// Clear database
MATCH (n) DETACH DELETE n;

// Create index
CREATE INDEX user_id IF NOT EXISTS FOR (u:User) ON (u.id);

CREATE (u1:User {id: '1', username: 'Adrian'}),
       (u2:User {id: '2', username: 'Monika'}),
       (u3:User {id: '3', username: 'Azazel'}),
       (u4:User {id: '4', username: 'Robert'}),
       (u5:User {id: '5', username: 'Aleksandra'}),
       (u6:User {id: '6', username: 'Michał'}),
       (u7:User {id: '7', username: 'Katarzyna'}),
       (u8:User {id: '8', username: 'Mateusz'}),
       (u9:User {id: '9', username: 'Zofia'}),
       (u10:User {id: '10', username: 'Jan'}),
       (u11:User {id: '11', username: 'Julia'}),
       (u12:User {id: '12', username: 'Tomasz'}),
       (u13:User {id: '13', username: 'Anna'}),
       (u14:User {id: '14', username: 'Piotr'}),
       (u15:User {id: '15', username: 'Natalia'}),
       (u16:User {id: '16', username: 'Paweł'}),
       (u17:User {id: '17', username: 'Maria'}),
       (u18:User {id: '18', username: 'Krzysztof'}),
       (u19:User {id: '19', username: 'Emilia'}),
       (u20:User {id: '20', username: 'Marcin'}),
       (u21:User {id: '21', username: 'Maja'}),
       (u22:User {id: '22', username: 'Łukasz'}),
       (u23:User {id: '23', username: 'Amelia'}),
       (u24:User {id: '24', username: 'Grzegorz'}),
       (u25:User {id: '25', username: 'Alicja'}),
       (u26:User {id: '26', username: 'Adam'}),
       (u27:User {id: '27', username: 'Martyna'}),
       (u28:User {id: '28', username: 'Rafał'}),
       (u29:User {id: '29', username: 'Ewelina'}),
       (u30:User {id: '30', username: 'Maciej'}),
       (u31:User {id: '31', username: 'Zygfryd'}),
       (u32:User {id: '32', username: 'Jakub'}),
       (u33:User {id: '33', username: 'Agnieszka'}),
       (u34:User {id: '34', username: 'Hubert'}),
       (u35:User {id: '35', username: 'Gabriela'}),
       (u36:User {id: '36', username: 'Dawid'}),
       (u37:User {id: '37', username: 'Lena'}),
       (u38:User {id: '38', username: 'Szymon'}),
       (u39:User {id: '39', username: 'Barbara'}),
       (u40:User {id: '40', username: 'Oliwier'}),
       (u41:User {id: '41', username: 'Nikola'}),
       (u42:User {id: '42', username: 'Wojciech'}),
       (u43:User {id: '43', username: 'Karolina'}),
       (u44:User {id: '44', username: 'Wiktor'}),
       (u45:User {id: '45', username: 'Kinga'}),
       (u46:User {id: '46', username: 'Artur'}),
       (u47:User {id: '47', username: 'Oliwia'}),
       (u48:User {id: '48', username: 'Patryk'}),
       (u49:User {id: '49', username: 'Joanna'}),
       (u50:User {id: '50', username: 'Damian'}),
       (u51:User {id: '51', username: 'Patrycja'}),
       (u52:User {id: '52', username: 'Filip'}),
       (u53:User {id: '53', username: 'Sandra'}),
       (u54:User {id: '54', username: 'Sebastian'}),
       (u55:User {id: '55', username: 'Izabela'}),
       (u56:User {id: '56', username: 'Daniel'}),
       (u57:User {id: '57', username: 'Beata'}),
       (u58:User {id: '58', username: 'Konrad'}),
       (u59:User {id: '59', username: 'Klaudia'}),
       (u60:User {id: '60', username: 'Bartłomiej'}),
       (u61:User {id: '61', username: 'Renata'}),
       (u62:User {id: '62', username: 'Igor'}),
       (u63:User {id: '63', username: 'Edyta'}),
       (u64:User {id: '64', username: 'Kamil'}),
       (u65:User {id: '65', username: 'Magdalena'}),
       (u66:User {id: '66', username: 'Bartosz'}),
       (u67:User {id: '67', username: 'Małgorzata'}),
       (u68:User {id: '68', username: 'Witold'}),
       (u69:User {id: '69', username: 'Justyna'}),
       (u70:User {id: '70', username: 'Marian'}),
       (u71:User {id: '71', username: 'Iwona'}),
       (u72:User {id: '72', username: 'Jerzy'}),
       (u73:User {id: '73', username: 'Dorota'}),
       (u74:User {id: '74', username: 'Leszek'}),
       (u75:User {id: '75', username: 'Zuzanna'}),
       (u76:User {id: '76', username: 'Cezary'}),
       (u77:User {id: '77', username: 'Aleksander'}),
       (u78:User {id: '78', username: 'Oskar'}),
       (u79:User {id: '79', username: 'Halina'}),
       (u80:User {id: '80', username: 'Leon'}),
       (u81:User {id: '81', username: 'Elżbieta'}),
       (u82:User {id: '82', username: 'Kazimierz'}),
       (u83:User {id: '83', username: 'Weronika'}),
       (u84:User {id: '84', username: 'Andrzej'}),
       (u85:User {id: '85', username: 'Grażyna'}),
       (u86:User {id: '86', username: 'Jacek'}),
       (u87:User {id: '87', username: 'Michalina'}),
       (u88:User {id: '88', username: 'Przemysław'}),
       (u89:User {id: '89', username: 'Hanna'}),
       (u90:User {id: '90', username: 'Bogdan'}),
       (u91:User {id: '91', username: 'Sylwia'}),
       (u92:User {id: '92', username: 'Borys'}),
       (u93:User {id: '93', username: 'Ludwika'}),
       (u94:User {id: '94', username: 'Norbert'}),
       (u95:User {id: '95', username: 'Roksana'}),
       (u96:User {id: '96', username: 'Fryderyk'}),
       (u97:User {id: '97', username: 'Jolanta'}),
       (u1)-[:KNOWS]->(u5),
       (u1)-[:KNOWS]->(u20),
       (u1)-[:KNOWS]->(u54),
       (u2)-[:KNOWS]->(u14),
       (u2)-[:KNOWS]->(u45),
       (u3)-[:KNOWS]->(u6),
       (u3)-[:KNOWS]->(u31),
       (u3)-[:KNOWS]->(u77),
       (u4)-[:KNOWS]->(u2),
       (u4)-[:KNOWS]->(u34),
       (u4)-[:KNOWS]->(u83),
       (u6)-[:KNOWS]->(u95),
       (u7)-[:KNOWS]->(u51),
       (u8)-[:KNOWS]->(u17),
       (u8)-[:KNOWS]->(u20),
       (u8)-[:KNOWS]->(u79),
       (u9)-[:KNOWS]->(u29),
       (u11)-[:KNOWS]->(u21),
       (u11)-[:KNOWS]->(u78),
       (u13)-[:KNOWS]->(u5),
       (u13)-[:KNOWS]->(u24),
       (u13)-[:KNOWS]->(u40),
       (u13)-[:KNOWS]->(u75),
       (u13)-[:KNOWS]->(u76),
       (u14)-[:KNOWS]->(u26),
       (u14)-[:KNOWS]->(u67),
       (u17)-[:KNOWS]->(u21),
       (u17)-[:KNOWS]->(u30),
       (u17)-[:KNOWS]->(u42),
       (u18)-[:KNOWS]->(u83),
       (u18)-[:KNOWS]->(u95),
       (u19)-[:KNOWS]->(u87),
       (u20)-[:KNOWS]->(u40),
       (u20)-[:KNOWS]->(u86),
       (u22)-[:KNOWS]->(u22),
       (u22)-[:KNOWS]->(u28),
       (u22)-[:KNOWS]->(u92),
       (u24)-[:KNOWS]->(u2),
       (u25)-[:KNOWS]->(u15),
       (u25)-[:KNOWS]->(u31),
       (u27)-[:KNOWS]->(u75),
       (u28)-[:KNOWS]->(u3),
       (u28)-[:KNOWS]->(u6),
       (u28)-[:KNOWS]->(u17),
       (u28)-[:KNOWS]->(u83),
       (u28)-[:KNOWS]->(u84),
       (u29)-[:KNOWS]->(u87),
       (u31)-[:KNOWS]->(u3),
       (u31)-[:KNOWS]->(u7),
       (u31)-[:KNOWS]->(u66),
       (u32)-[:KNOWS]->(u97),
       (u33)-[:KNOWS]->(u8),
       (u34)-[:KNOWS]->(u51),
       (u34)-[:KNOWS]->(u63),
       (u36)-[:KNOWS]->(u59),
       (u37)-[:KNOWS]->(u31),
       (u37)-[:KNOWS]->(u68),
       (u37)-[:KNOWS]->(u80),
       (u38)-[:KNOWS]->(u27),
       (u38)-[:KNOWS]->(u78),
       (u39)-[:KNOWS]->(u46),
       (u40)-[:KNOWS]->(u14),
       (u40)-[:KNOWS]->(u39),
       (u40)-[:KNOWS]->(u47),
       (u40)-[:KNOWS]->(u52),
       (u40)-[:KNOWS]->(u80),
       (u40)-[:KNOWS]->(u82),
       (u41)-[:KNOWS]->(u75),
       (u42)-[:KNOWS]->(u11),
       (u42)-[:KNOWS]->(u20),
       (u42)-[:KNOWS]->(u30),
       (u42)-[:KNOWS]->(u72),
       (u43)-[:KNOWS]->(u92),
       (u44)-[:KNOWS]->(u6),
       (u44)-[:KNOWS]->(u95),
       (u45)-[:KNOWS]->(u18),
       (u45)-[:KNOWS]->(u54),
       (u45)-[:KNOWS]->(u62),
       (u46)-[:KNOWS]->(u36),
       (u47)-[:KNOWS]->(u95),
       (u48)-[:KNOWS]->(u52),
       (u49)-[:KNOWS]->(u16),
       (u49)-[:KNOWS]->(u18),
       (u49)-[:KNOWS]->(u65),
       (u50)-[:KNOWS]->(u34),
       (u51)-[:KNOWS]->(u9),
       (u51)-[:KNOWS]->(u53),
       (u51)-[:KNOWS]->(u70),
       (u52)-[:KNOWS]->(u63),
       (u54)-[:KNOWS]->(u20),
       (u56)-[:KNOWS]->(u19),
       (u56)-[:KNOWS]->(u21),
       (u57)-[:KNOWS]->(u43),
       (u57)-[:KNOWS]->(u62),
       (u58)-[:KNOWS]->(u15),
       (u59)-[:KNOWS]->(u25),
       (u59)-[:KNOWS]->(u37),
       (u59)-[:KNOWS]->(u70),
       (u60)-[:KNOWS]->(u5),
       (u62)-[:KNOWS]->(u54),
       (u63)-[:KNOWS]->(u29),
       (u63)-[:KNOWS]->(u80),
       (u64)-[:KNOWS]->(u73),
       (u65)-[:KNOWS]->(u89),
       (u68)-[:KNOWS]->(u55),
       (u68)-[:KNOWS]->(u91),
       (u71)-[:KNOWS]->(u3),
       (u72)-[:KNOWS]->(u6),
       (u72)-[:KNOWS]->(u74),
       (u72)-[:KNOWS]->(u84),
       (u73)-[:KNOWS]->(u3),
       (u73)-[:KNOWS]->(u14),
       (u75)-[:KNOWS]->(u8),
       (u75)-[:KNOWS]->(u28),
       (u76)-[:KNOWS]->(u27),
       (u76)-[:KNOWS]->(u28),
       (u76)-[:KNOWS]->(u75),
       (u77)-[:KNOWS]->(u39),
       (u77)-[:KNOWS]->(u73),
       (u78)-[:KNOWS]->(u71),
       (u79)-[:KNOWS]->(u11),
       (u79)-[:KNOWS]->(u62),
       (u80)-[:KNOWS]->(u10),
       (u81)-[:KNOWS]->(u51),
       (u82)-[:KNOWS]->(u26),
       (u82)-[:KNOWS]->(u33),
       (u82)-[:KNOWS]->(u47),
       (u83)-[:KNOWS]->(u2),
       (u83)-[:KNOWS]->(u12),
       (u83)-[:KNOWS]->(u82),
       (u84)-[:KNOWS]->(u18),
       (u84)-[:KNOWS]->(u74),
       (u85)-[:KNOWS]->(u29),
       (u86)-[:KNOWS]->(u93),
       (u88)-[:KNOWS]->(u32),
       (u88)-[:KNOWS]->(u71),
       (u89)-[:KNOWS]->(u85),
       (u91)-[:KNOWS]->(u57),
       (u91)-[:KNOWS]->(u65),
       (u91)-[:KNOWS]->(u82),
       (u92)-[:KNOWS]->(u51),
       (u93)-[:KNOWS]->(u27),
       (u93)-[:KNOWS]->(u56),
       (u94)-[:KNOWS]->(u37),
       (u95)-[:KNOWS]->(u17),
       (u95)-[:KNOWS]->(u21),
       (u95)-[:KNOWS]->(u40),
       (u96)-[:KNOWS]->(u4),
       (u96)-[:KNOWS]->(u85),
       (u97)-[:KNOWS]->(u84);