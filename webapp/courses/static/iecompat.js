    // Production steps of ECMA-262, Edition 5, 15.4.4.19  
    // Reference: http://es5.github.com/#x15.4.4.19  
    if (!Array.prototype.map) {  
      Array.prototype.map = function(callback, thisArg) {  
      
        var T, A, k;  
      
        if (this == null) {  
          throw new TypeError(" this is null or not defined");  
        }  
      
        // 1. Let O be the result of calling ToObject passing the |this| value as the argument.  
        var O = Object(this);  
      
        // 2. Let lenValue be the result of calling the Get internal method of O with the argument "length".  
        // 3. Let len be ToUint32(lenValue).  
        var len = O.length >>> 0;  
      
        // 4. If IsCallable(callback) is false, throw a TypeError exception.  
        // See: http://es5.github.com/#x9.11  
        if ({}.toString.call(callback) != "[object Function]") {  
          throw new TypeError(callback + " is not a function");  
        }  
      
        // 5. If thisArg was supplied, let T be thisArg; else let T be undefined.  
        if (thisArg) {  
          T = thisArg;  
        }  
      
        // 6. Let A be a new array created as if by the expression new Array(len) where Array is  
        // the standard built-in constructor with that name and len is the value of len.  
        A = new Array(len);  
      
        // 7. Let k be 0  
        k = 0;  
      
        // 8. Repeat, while k < len  
        while(k < len) {  
      
          var kValue, mappedValue;  
      
          // a. Let Pk be ToString(k).  
          //   This is implicit for LHS operands of the in operator  
          // b. Let kPresent be the result of calling the HasProperty internal method of O with argument Pk.  
          //   This step can be combined with c  
          // c. If kPresent is true, then  
          if (k in O) {  
      
            // i. Let kValue be the result of calling the Get internal method of O with argument Pk.  
            kValue = O[ k ];  
      
            // ii. Let mappedValue be the result of calling the Call internal method of callback  
            // with T as the this value and argument list containing kValue, k, and O.  
            mappedValue = callback.call(T, kValue, k, O);  
      
            // iii. Call the DefineOwnProperty internal method of A with arguments  
            // Pk, Property Descriptor {Value: mappedValue, Writable: true, Enumerable: true, Configurable: true},  
            // and false.  
      
            // In browsers that support Object.defineProperty, use the following:  
            // Object.defineProperty(A, Pk, { value: mappedValue, writable: true, enumerable: true, configurable: true });  
      
            // For best browser support, use the following:  
            A[ k ] = mappedValue;  
          }  
          // d. Increase k by 1.  
          k++;  
        }  
      
        // 9. return A  
        return A;  
      };        
    }  
    
    
/* Cross-Browser Split 1.0.1
(c) Steven Levithan <stevenlevithan.com>; MIT License
An ECMA-compliant, uniform cross-browser split method */

var cbSplit;

// avoid running twice, which would break `cbSplit._nativeSplit`'s reference to the native `split`
if (!cbSplit) {

cbSplit = function (str, separator, limit) {
    // if `separator` is not a regex, use the native `split`
    if (Object.prototype.toString.call(separator) !== "[object RegExp]") {
        return cbSplit._nativeSplit.call(str, separator, limit);
    }

    var output = [],
        lastLastIndex = 0,
        flags = (separator.ignoreCase ? "i" : "") +
                (separator.multiline  ? "m" : "") +
                (separator.sticky     ? "y" : ""),
        separator = RegExp(separator.source, flags + "g"), // make `global` and avoid `lastIndex` issues by working with a copy
        separator2, match, lastIndex, lastLength;

    str = str + ""; // type conversion
    if (!cbSplit._compliantExecNpcg) {
        separator2 = RegExp("^" + separator.source + "$(?!\\s)", flags); // doesn't need /g or /y, but they don't hurt
    }

    /* behavior for `limit`: if it's...
    - `undefined`: no limit.
    - `NaN` or zero: return an empty array.
    - a positive number: use `Math.floor(limit)`.
    - a negative number: no limit.
    - other: type-convert, then use the above rules. */
    if (limit === undefined || +limit < 0) {
        limit = Infinity;
    } else {
        limit = Math.floor(+limit);
        if (!limit) {
            return [];
        }
    }

    while (match = separator.exec(str)) {
        lastIndex = match.index + match[0].length; // `separator.lastIndex` is not reliable cross-browser

        if (lastIndex > lastLastIndex) {
            output.push(str.slice(lastLastIndex, match.index));

            // fix browsers whose `exec` methods don't consistently return `undefined` for nonparticipating capturing groups
            if (!cbSplit._compliantExecNpcg && match.length > 1) {
                match[0].replace(separator2, function () {
                    for (var i = 1; i < arguments.length - 2; i++) {
                        if (arguments[i] === undefined) {
                            match[i] = undefined;
                        }
                    }
                });
            }

            if (match.length > 1 && match.index < str.length) {
                Array.prototype.push.apply(output, match.slice(1));
            }

            lastLength = match[0].length;
            lastLastIndex = lastIndex;

            if (output.length >= limit) {
                break;
            }
        }

        if (separator.lastIndex === match.index) {
            separator.lastIndex++; // avoid an infinite loop
        }
    }

    if (lastLastIndex === str.length) {
        if (lastLength || !separator.test("")) {
            output.push("");
        }
    } else {
        output.push(str.slice(lastLastIndex));
    }

    return output.length > limit ? output.slice(0, limit) : output;
};

cbSplit._compliantExecNpcg = /()??/.exec("")[1] === undefined; // NPCG: nonparticipating capturing group
cbSplit._nativeSplit = String.prototype.split;

} // end `if (!cbSplit)`

// for convenience...
String.prototype.split = function (separator, limit) {
    return cbSplit(this, separator, limit);
};
