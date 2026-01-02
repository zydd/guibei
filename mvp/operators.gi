#
unaryr ?
unaryr !  beside ?
infix ??  beside ?  # cannot mix with operators of the same precedence, e.g: a??b?

#
infixr ** below ?

#
unaryl +  below **
unaryl -  below **
unaryl ~  below **

#
infixl *  below unaryl +
infixl /  below unaryl +
infixl // below unaryl +
infixl %  below unaryl +

#
infixl +  below *
infixl -  below *

#
infixl << below infixl +
infixl >> below infixl +

#
infixl &  below <<

#
infixl ^  below &

#
infixl |  below ^

#
infix ==  below |
infix !=  below |
infix >=  below |
infix <=  below |
infix >   below |
infix <   below |

#
infixr && below ==

#
infixr || below &&

#
infix ..  below ||

#
infixr $  below ..
